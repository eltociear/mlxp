.. _logging:

2- Logging 
----------


Logging metrics and artifacts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The logger provides four methods for logging objects:
    
    - :samp:`log_metrics`: For logging dictionaries of scalars in a json file. This method can be used to log the loss and other scalar quantities that can evolve during the run. These dictionaries are stored in a json file.
    - :samp:`log_artifacts`: For logging more complex objects such as the weights of a network, etc. This method requires passing objects inheriting from the abstract class :samp:`Artifacts`.
    - :samp:`log_checkpoint`: A simpler method for logging serializable objects as a pickle file.
    - :samp:`load_checkpoint`: A method for loading a saved checkpoint.


File structure of the logs
^^^^^^^^^^^^^^^^^^^^^^^^^^

When the logger is activated, it stores the results of a run in a sub-directory of the parent directory :samp:`./logs`. This parent directory is created automatically if it does not exists already. By default it is set to :samp:`./logs`, but this behavior can be modified (see :ref:`Customizing the parent log directory <custom_log_dir>`).

First, the logger assigns a :samp:`log_id` to the run. Every time :samp:`main.py` is executed with an active logger, the :samp:`log_id` of the new run is incremented by 1 starting from 1. Then a new sub-directory of :samp:`./logs` is created and named after the assigned :samp:`log_id`. 
Since we executed the code three times in total, we should expect three sub-directories under :samp:`./logs` called :samp:`1`, :samp:`2` and :samp:`3`, all having the same structure:

.. code-block:: text
   :caption: ./logs/

   logs/
   ├── 1/...
   ├── 2/...
   └── 3/...


Each log directory contains three sub-directories: :samp:`metadata`, :samp:`metrics` and :samp:`artifacts`:

.. code-block:: text
   :caption: ./logs/

   logs/
   ├── 1/
   │   ├── metadata/
   │   │   ├── config.yaml
   │   │   ├── info.yaml
   │   │   └── mlxp.yaml
   │   ├── metrics/
   │   │   ├── train.json
   │   │   └──.keys/
   │   │       └── metrics.yaml
   │   └── artifacts/
   │       └── Checkpoint/
   │           └── last_ckpt.pkl
   │    
   ├── 2/...
   └── 3/...

Let's go through these three directories.

The :samp:`metrics` directory
"""""""""""""""""""""""""""""

This directory contains JSON files created when calling the logger's method 
:samp:`log_metrics(dict, log_name)`. 
Each file is named after the variable :samp:`log_name` and stores the dictionaries provided as input to the :samp:`log_metrics` method.


.. code-block:: json
    :caption: ./logs/1/metrics/train.json

    {"loss": 0.030253788456320763, "epoch": 0}
    {"loss": 0.02899891696870327, "epoch": 1}
    {"loss": 0.026649776846170425, "epoch": 2}
    {"loss": 0.023483652621507645, "epoch": 3}
    {"loss": 0.019827445968985558, "epoch": 4}
    {"loss": 0.01599641889333725, "epoch": 5}
    {"loss": 0.012259905226528645, "epoch": 6}
    {"loss": 0.008839688263833523, "epoch": 7}
    {"loss": 0.005932427477091551, "epoch": 8}
    {"loss": 0.003738593542948365, "epoch": 9}

The hidden directory :samp:`.keys` is used by the reader module of MLXP and is not something to worry about here. Instead, we inspect the remaining directories below. 


The :samp:`metadata` directory
""""""""""""""""""""""""""""""

The :samp:`metadata`  directory contains three yaml files: :samp:`config`, :samp:`info`, and :samp:`mlxp`, each storing the content of the corresponding fields of the context object :samp:`ctx`. 
:samp:`config` stores the user config of the run, :samp:`info` stores general information about the run such as the assigned :samp:`log_id` and the absolute path to the logs of the run :samp:`log_dir`. Finally, :samp:`mlxp` stores the MLXP's settings used for the run (e.g. the logger settings). 

.. code-block:: yaml
    :caption: ./logs/1/metadata/config.yaml

    seed: 0
    num_epoch: 10
    model:
     num_units: 100
    data:
     d_int: 10
     device: 'cpu'
    optimizer:
     lr: 10.

.. code-block:: yaml
    :caption: ./logs/1/metadata/info.yaml
    
    executable: absolute_path_to/bin/python
    cmd: ''
    end_date: 20/04/2023
    end_time: '16:01:13'
    current_file_path: absolute_path_to/main.py
    log_dir: absolute_path_to/logs/1
    log_id: 1
    process_id: 7100
    start_date: 20/04/2023
    start_time: '16:01:13'
    status: COMPLETE
    user: marbel
    work_dir: absolute_path_to/tutorial

.. code-block:: yaml
    :caption: ./logs/1/metadata/mlxp.yaml

    logger:
      forced_log_id: -1
      log_streams_to_file: false
      name: DefaultLogger
      parent_log_dir: ./logs
    scheduler:
      cleanup_cmd: ''
      env_cmd: ''
      name: NoScheduler
      option_cmd: []
      shell_config_cmd: ''
      shell_path: /bin/bash
    version_manager:
      name: GitVM
      parent_work_dir: ./.workdir
      compute_requirements: false
    use_logger: true
    use_scheduler: false
    use_version_manager: false
    interactive_mode: true


The :samp:`artifacts` directory 
"""""""""""""""""""""""""""""""

The directory :samp:`artifacts` is where all data passed to the logger's methods :samp:`log_artifacts` and :samp:`log_checkpoint` are stored. 
These are stored in different directories depending on the artifact type. In this example, since we used the reserved method :samp:`log_checkpoint`, the logged data are considered as checkpoint objects, hence the sub-directory :samp:`Checkpoint`. 
You can see that it contains the pickle file :samp:`last_ckpt.pkl` which is the name we provided when calling the method :samp:`log_checkpoint` in the :samp:`main.py` file. 




Checkpointing
^^^^^^^^^^^^^

Checkpointing can be particularly useful if you need to restart a job from its latest state without having to re-run it from scratch. To do this, you only need to slightly modify the function :samp:`train` to load the latest checkpoint by default:

.. code-block:: python
    :caption: main.py

    import torch
    from core import DataLoader, OneHiddenLayer

    import mlxp

    @mlxp.launch(config_path='./configs')
    def train(ctx: mlxp.Context)->None:

        cfg = ctx.config
        logger = ctx.logger

        # Try loading from the checkpoint
        try:
            checkpoint = logger.load_checkpoint()
            start_epoch = checkpoint['epoch']+1
            model = checkpoint['model']
        except:
            start_epoch = 0
            model = Network(n_layers = cfg.model.num_layers)


        model = model.to(cfg.data.device)
        optimizer = torch.optim.SGD(model.parameters(),
                                    lr=cfg.optimizer.lr)
        dataloader = DataLoader(cfg.data.d_int,
                                cfg.data.device)         

        # Training
        print(f"Starting from epoch: {start_epoch} ")

        for epoch in range(start_epoch,cfg.num_epoch):

            train_err = train_epoch(dataloader,
                                    model,
                                    optimizer)

            logger.log_metrics({'loss': train_err.item(),
                                'epoch': epoch}, log_name='train')
            
            logger.log_checkpoint({'model': model,
                                   'epoch':epoch}, log_name='last_ckpt' )

        print(f"Completed training with learing rate: {cfg.optimizer.lr}")


    if __name__ == "__main__":
        train()

Of course, if you execute :samp:`main.py` without further options, the logger will create a new :samp:`log_id` where there is no checkpoint yet, so it cannot resume a previous job. Instead, you need to force the :samp:`log_id` using the option :samp:`logger.forced_log_id`:

.. code-block:: console

   $ python main.py +mlxp.logger.forced_log_id=1
   Starting from epoch 10
   Completed training with learning rate: 1e-3

.. _custom_log_dir:

Customizing the parent log directory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can change the parent directory by overriding the option :samp:`+mlxp.logger.parent_log_dir` from the command-line:

.. code-block:: console

   $ python main.py +mlxp.logger.parent_log_dir='./new_logs'


Alternatively, the parent directory can be modified directly in the MLXP default settings file :samp:`configs/mlxp.yaml`. This file is created automatically if it doesn't exist already and contains all the defaults options for using MLXP in the current project:

.. code-block:: yaml
   :caption: ./configs/mlxp.yaml

   logger:
     ...
     parent_log_dir: ./logs
     ...
