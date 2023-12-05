"""The version manager allows to keep track of changes to the code and to automatically
generate a deployment version of the code based on the latest git commit."""

import abc
import os
import subprocess
from typing import Any, Dict

import yaml

from mlxp._internal._interactive_mode import _bcolors, _printc


ignore_untracked_msg = _bcolors.FAIL + "Warning:" + _bcolors.ENDC + "There are untracked files! \n"
ignore_untracked_msg += (
    _bcolors.FAIL
    + "Warning:"
    + _bcolors.ENDC
    + "Untracked files will not be accessible during execution of the run!"
)

ignore_uncommited_msg = _bcolors.FAIL + "Warning:" + _bcolors.ENDC + "Run will be executed from the latest commit\n"

ignore_uncommited_msg += (
    _bcolors.FAIL
    + "Warning:"
    + _bcolors.ENDC
    + "Uncommitted changes will not be taken into account during execution of the run!\n"
    )



class VersionManager(abc.ABC):
    """An abstract class whose children allow custumizing the working directory of the
    run."""

    def __init__(self):
        self.im_handler = None

    def _set_im_handler(self, im_handler: Any) -> None:
        self.im_handler = im_handler
        im_handler_choice = self.im_handler.get_im_choice("vm")
        self._existing_choices = im_handler_choice is not None
        if not self._existing_choices:
            self.im_handler.set_im_choice("vm",True)


    @abc.abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Return a dictionary containing information about the version used for the
        run.

        :return: Dictionary containing information about the version used for the run.
        :rtype: Dict[str, Any]
        """
        pass

    @abc.abstractmethod
    def make_working_directory(self) -> str:
        """Return a path to the target working directory from which runs submitted to a
        cluster in batch mode will be executed.

        :rtype: str
        :return: A path to the target working directory
        """
        pass


class GitVM(VersionManager):
    """GitVM allows separting development code from code deployed in a cluster and
    allows to recover exactly the code used for a given run.

    GitVM creates a copy of the current directory based on the latest commit,
    if it doesn't exist already, then sets the working directory to this copy.

    .. py:attribute:: parent_work_dir
        :type: str

        The target parent directory of
        the new working directory returned by the version manager

    .. py:attribute:: compute_requirements
        :type: bool

        When set to true, the version manager stores a list of requirements and their version.
    """

    def __init__(self, parent_work_dir: str, compute_requirements: bool):
        super().__init__()

        self.parent_work_dir = os.path.abspath(parent_work_dir)
        self.compute_requirements = compute_requirements
        self.dst = None
        self.commit_hash = None
        self.repo_path = None
        self.work_dir = os.getcwd()
        self.requirements = ["UNKNOWN"]




    def get_info(self) -> Dict[str, Any]:
        """Return a dictionary containing information about the version used for the
        run.

        The following information is returned:
        - requirements: the dependencies of the code and their versions. Empty if no requirements file was found.
        - commit_hash: The hash of the latest commit.
        - repo_path: Path to the repository.

        :return: Dictionary containing
        information about the version used for the run.
        :rtype: Dict[str, Any]
        """
        return {
            "requirements": self.requirements,
            "commit_hash": self.commit_hash,
            "repo_path": self.repo_path,
        }

    def make_working_directory(self) -> str:
        """Create and return a target working directory.

        Depending on the user's choice, the returned directory is either:

        - The current working directory.
        - A directory under self.parent_work_dir/repo_name/latest_commit_hash.
        In this case, a copy of the code based on the latest git commit is created and used to run the experiment.

        :rtype: str
        :return: A path to the target working directory
        """



        repo = self._getGitRepo()
        repo_root = repo.git.rev_parse("--show-toplevel")
        relpath = os.path.relpath(os.getcwd(), repo_root)
        self.repo_path = repo.working_tree_dir
        

        self._handle_cloning(repo,relpath)


        if not self._existing_choices:
            self.im_handler._save_im_choice()

        return self.work_dir


    def _clone_repo(self, repo):
        repo_name = self.repo_path.split("/")[-1]
        self.commit_hash = repo.head.object.hexsha
        target_name = os.path.join(repo_name, self.commit_hash)
        parent_work_dir = self.parent_work_dir
        self.dst = os.path.join(parent_work_dir, target_name)

        if not os.path.isdir(self.dst):
            _printc(_bcolors.OKBLUE, f"Creating a backup of the code at {self.dst}")
            repo.clone(self.dst)
            if self.compute_requirements:
                self._make_requirements_file()
        else:
            if not self._existing_choices:
                _printc(
                    _bcolors.OKBLUE,
                    f"Found a backup of the code with commit-hash: {self.commit_hash}",
                )
                _printc(_bcolors.OKBLUE, f"Run will be executed from {self.dst}")


    def _handle_cloning(self,repo,relpath):
        choice = "y"
        while True:
            if self.im_handler._interactive_mode:
                valid_choice = True
                if self._existing_choices:
                    choice = self.im_handler.get_im_choice("cloning")
                    valid_choice = choice in ["y", "n"]

                inexisting_choice = (not self._existing_choices) or not valid_choice  
                if inexisting_choice:
                    choice = _get_cloning_choice()
                    self.im_handler.set_im_choice("cloning",choice)
                    if choice=="y":
                        _printc(_bcolors.OKBLUE,
                            f"Run will be executed from a backup directory based on the latest commit ")

                
            if choice == "y":
                self._handle_untracked_files(repo)
                self._handle_commit_state(repo)
                self._clone_repo(repo)
                self._set_requirements()
                self.work_dir = os.path.join(self.dst, relpath)
                break
            elif choice == "n":
                if not self._existing_choices:
                    _printc(
                        _bcolors.OKBLUE,
                        f"Run will be executed from the main directory",
                    )
                    _printc(
                        _bcolors.OKBLUE,
                        f"Warning: [Reproduciblity] Run is not linked to any git commit",
                    )


                break
            else:
                _printc(_bcolors.OKBLUE, "Invalid choice. Please try again. (y/n)")
        return choice




    def _handle_commit_state(self, repo):
        while True:
            if repo.is_dirty():
                _printc(_bcolors.OKBLUE, "There are uncommitted changes!\n")
                if self.im_handler._interactive_mode:
                    if self._existing_choices:
                        break
                    else:
                        done = _is_done_uncommited_changes(repo)
                        if done:
                            break
                else:


                    print(ignore_uncommited_msg)          
            else:
                _printc(_bcolors.OKBLUE, "No uncommitted changes!")
                break


    def _handle_untracked_files(self, repo):

        while True:
            if repo.untracked_files:
                if self.im_handler._interactive_mode:
                    if self._existing_choices:
                        break
                    status = repo.git.status()
                    print(status)
                    done = _is_done_untracked_files(repo)
                    if done:
                        break
                else:

                    print(ignore_untracked_msg)

            else:
                _printc(_bcolors.OKBLUE, "No untracked files!")
                _printc(_bcolors.OKBLUE, "Continuing checks ...")    
                break

    def _make_requirements_file(self):
        _printc(_bcolors.OKBLUE, "No requirements file found")
        _printc(_bcolors.OKBLUE, "Generating it using pipreqs")
        # Create a new updated requirement file.
        reqs_cmd = f"pipreqs --force {self.dst}"
        subprocess.check_call(reqs_cmd, shell=True)

    def _set_requirements(self):
        fname = os.path.join(self.dst, "requirements.txt")

        if os.path.exists(fname) or not self.compute_requirements:
            pass
        else:
            self._make_requirements_file()

        if os.path.exists(fname):
            with open(fname, "r") as file:
                # Read the contents of the file
                contents = file.read()
                # Split the contents into lines
                lines = contents.splitlines()
                # Create a list of package names
                package_list = []
                # Iterate through the lines and append each line (package name) to the
                # list
                for line in lines:
                    package_list.append(line)
            self.requirements = package_list

    def _getGitRepo(self):
        import git

        try:
            repo = git.Repo(search_parent_directories=True)
        except git.exc.InvalidGitRepositoryError:
            msg = os.getcwd() + ". To use the GitVM version manager, the code must belong to a git repository!"
            raise git.exc.InvalidGitRepositoryError(msg)


        return repo


def _disp_uncommited_files(repo):
    unstaged_files = repo.index.diff(None)
    staged_files = repo.index.diff("HEAD", staged=True)
    all_files = unstaged_files + staged_files
    for change in all_files:
        file_name = change.a_path
        _printc(_bcolors.FAIL, file_name)


def _disp_untracked_files(repo):
    from git.compat import defenc

    status = repo.git.status(porcelain=True, untracked_files=False, as_process=True)

    prefix = "?? "
    untracked_files = []
    for line in status.stdout:
        line = line.decode(defenc)
        if not line.startswith(prefix):
            continue
        filename = line[len(prefix) :].rstrip("\n")
        # Special characters are escaped
        if filename[0] == filename[-1] == '"':
            filename = filename[1:-1]
            # WHATEVER ... it's a mess, but works for me
            filename = filename.encode("ascii").decode("unicode_escape").encode("latin1").decode(defenc)
        untracked_files.append(filename)

    for name in untracked_files:
        _printc(_bcolors.FAIL, name)


def _get_cloning_choice():
    _printc(
        _bcolors.OKGREEN,
        "Would you like to execute code from a backup copy based on the latest commit? (y/n):",
    )
    print(
            f"{_bcolors.OKGREEN}a{_bcolors.ENDC}: Yes (Recommended option)"
        )
    print(f"{_bcolors.OKGREEN}b{_bcolors.ENDC}: No. (Code will be executed from the main repository)")
    choice = input(f"{_bcolors.OKGREEN}Please enter you answer (y/n):{_bcolors.ENDC}")
    return choice


def _is_done_uncommited_changes(repo):
    done = False
    choice = _get_choice_uncommited_changes(repo)
    if repo.is_dirty():
        if choice =="y":
            _printc(_bcolors.OKBLUE, "Commiting changes....")
            output_msg = repo.git.commit("-a", "-m", "mlxp: Automatically committing all changes")
            _printc(_bcolors.OKBLUE, output_msg)
            done = True
        elif choice=="n":
            print(ignore_uncommited_msg)
            done = True
        else:
            _printc(_bcolors.OKBLUE, "Invalid choice. Please try again. (y/n)")
    else:
        _printc(_bcolors.OKBLUE, "No more uncommitted changes were found!")
        done = True        
    return done


def _is_done_untracked_files(repo):
    done = False
    choice = _get_choice_untracked_files(repo)
    if choice == "y":
        file_to_track = _get_files_to_track(repo)
        # If user input is not empty
        _add_files_to_track(repo, file_to_track)
        if repo.untracked_files:
            pass
        else:
            done = True
    elif choice == "n":
        print(ignore_untracked_msg)
        done = True
    else:
        _printc(_bcolors.OKBLUE, "Invalid choice. Please try again. (y/n)")

    return done

def _get_choice_uncommited_changes(repo):
    _printc(
        _bcolors.OKBLUE,
        "There are uncommitted changes in the repository:",
    )
    _disp_uncommited_files(repo)
    
    _printc(
        _bcolors.OKGREEN,
        "Would you like to create an automatic commit for all uncommitted changes? (y/n)",
    )
    print(
        f"{_bcolors.OKGREEN}y{_bcolors.ENDC}: Yes. "
    )
    print(f"{_bcolors.OKGREEN}n{_bcolors.ENDC}: No. Uncommitted changes will be ignored. (Before selecting this option, please make sure to manually handle uncommitted changes) ")
    choice = input(
        f"{_bcolors.OKGREEN}[Automatic commit]: Please enter your choice (y/n): {_bcolors.ENDC}"
    )

    return choice

def _get_choice_untracked_files(repo):
    _printc(_bcolors.OKBLUE, "There are untracked files in the repository:")
    _disp_untracked_files(repo)
    _printc(
        _bcolors.OKGREEN,
        "Would you like to add untracked files? (y/n)",
    )
    print(f"{_bcolors.OKGREEN}y{_bcolors.ENDC}: Yes.")
    # print(
    #     f"{_bcolors.OKGREEN}b{_bcolors.ENDC}: Check again for untrakced files (assuming you manually added them)."
    # )
    print(f"{_bcolors.OKGREEN}n{_bcolors.ENDC}: No. Untracked files will be ignored. (Before selecting this option, please make sure to manually add untracked files) ")
    choice = input(
        f"{_bcolors.OKGREEN}[Adding untracked files]: Please enter your choice (y/n):{_bcolors.ENDC}"
    )
    return choice

def _get_files_to_track(repo):
    print("Untracked files:")
    _disp_untracked_files(repo)
    _printc(
        _bcolors.OKGREEN,
        "Please select files to be tracked (comma-separated) and hit Enter to skip:",
    )

    files_input = input()
    return files_input

def _add_files_to_track(repo,files_to_track):
    if files_to_track:
        # Split user input by commas
        files_to_add = files_to_track.split(",")

        # Add selected files
        for file in files_to_add:
            repo.git.add(file.strip())
            _printc(_bcolors.OKGREEN,  file + " is added to the repository")
        # Commit the changes
        # repo.index.commit("mlxp: Committing selected files ")

