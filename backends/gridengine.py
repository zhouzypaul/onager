from datetime import timedelta
import os

from ._backend import Backend

class GridEngineBackend(Backend):
    def __init__(self):
        super().__init__()
        self.name = 'gridengine'
        self.header = """#!/bin/bash

source ./venv/bin/activate

"""
        self.body = """python -m worker {} {}
"""

        self.footer = """"""

        self.task_id_var = r'$SGE_TASK_ID'

    def generate_tasklist(self, commands, tasklist):
        if tasklist is None:
            ids = sorted(commands.keys())
            tasklist = ','.join(map(str,ids))
            # TODO: split into comma-separated blocks
        return tasklist

    def get_job_list(self, args):
        # Call the appropriate qsub command. The default behavior is to use
        # GridEngine's range feature, which starts a batch job with multiple tasks
        # and passes a different taskid to each one. If ntasks is zero, only a
        # single job is submitted with no subtasks.
        base_cmd = 'qsub '
        base_cmd += '-cwd ' # run script in current working directory

        # Duration and number of CPU/GPU resources
        #
        # Note that the Brown CS grid grants all GPU jobs infinite duration
        #  -l test   (10 min, high priority, limited to one slot per machine)
        #  -l short  (1 hour)
        #  -l long   (1 day)
        #  -l vlong  (infinite duration)
        #  -l gpus=# (infinite duration, on a GPU machine)
        duration = self.get_time_delta(args.duration)
        if args.gpus > 0:
            queue = 'gpu'
            base_cmd += '-l gpus={} '.format(args.gpus)# Request GPUs
        else:
            if duration > timedelta(days=1):
                queue = 'vlong'
            elif duration > timedelta(hours=1):
                queue = 'long'
            else:
                queue = 'short'
            base_cmd += '-l {} '.format(queue)
        if args.cpus > 1:
            base_cmd += '-pe smp {} '.format(args.nresources) # Request multiple CPUs

        # Memory requirements
        if args.mem > 1:
            base_cmd += '-l vf={}G '.format(args.mem)# Reserve extra memory  

        # if args.host is not None:
        #     base_cmd += '-q {}.q@{}.cs.brown.edu '.format(args.duration, args.host)

        base_cmd += '-o ./gridengine/logs/ ' # save stdout file to this directory
        base_cmd += '-e ./gridengine/logs/ ' # save stderr file to this directory

        # Logging
        log_dir = self.get_log_dir()
        # Format is jobname_jobid_taskid.*
        base_cmd += '-o {} '.format(os.path.join(log_dir, '${JOB_NAME}_${JOB_ID}_${TASK_ID}.o')) # save stdout to file
        base_cmd += '-e {} '.format(os.path.join(log_dir, '${JOB_NAME}_${JOB_ID}_${TASK_ID}.e')) # save stderr to file

        # The -terse flag causes qsub to print the jobid to stdout. We read the
        # jobid with subprocess.check_output(), and use it to delay the email job
        # until the entire batch job has completed.
        base_cmd += '-terse '

        # Prevent GridEngine from running this new job until the specified job ID is finished.
        if args.hold_jid is not None:
            base_cmd += "-hold_jid {} ".format(args.hold_jid)

        if args.maxtasks > 0:
            # set maximum number of running tasks per block
            base_cmd += "-tc {} ".format(args.maxtasks)

        wrapper_script = self.wrap_tasks(args.jobfile)
        wrapper_file = self.save_wrapper_script(wrapper_script, args.jobname)

        # Split tasklist into blocks that GridEngine can understand
        task_blocks = args.tasklist.split(',')
        return [base_cmd + "-t {} {}".format(task_block, wrapper_file) for task_block in task_blocks]