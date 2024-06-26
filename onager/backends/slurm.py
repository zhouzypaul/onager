from datetime import timedelta
import os

from ._backend import Backend
from ..subjobsfilemanager import SubjobsFileManager
from ..utils import compute_subjobs_filename, split_tasklist_into_subjob_groups

class SlurmBackend(Backend):
    def __init__(self):
        super().__init__()
        self.name = 'slurm'
        self.task_id_var = r'$SLURM_ARRAY_TASK_ID'
        self.job_id_var = r'$SLURM_ARRAY_JOB_ID'

    def get_cancel_cmds(self, cancellations):
        cmds = []
        for cancellation in cancellations:
            jobid, tasklist = cancellation
            cmd = "scancel"
            if tasklist is None:
                cmd += " {}".format(jobid)
            else:
                for task_id in tasklist:
                    cmd += " {}_{}".format(jobid, task_id)
            cmds.append(cmd)
        return cmds

    def get_job_list(self, args):
        # Call the appropriate sbatch command. The default behavior is to use
        # Slurm's job array feature, which starts a batch job with multiple tasks
        # and passes a different taskid to each one. If ntasks is zero, only a
        # single job is submitted with no subtasks.
        base_cmd = 'sbatch '
        base_cmd += '-J {} '.format(args.jobname)  # set name of job
        # Slurm runs scripts in current working directory by default

        # Duration
        base_cmd += '-t {} '.format(args.duration)
        duration = self.get_time_delta(args.duration)
        
        # account, partition, qos
        base_cmd += '--account={} '.format(args.account)
        base_cmd += '--partition={} '.format(args.partition)
        base_cmd += '--qos={} '.format(args.qos)

        # Number of CPU/GPU resources
        base_cmd += '--ntasks {} '.format(1)  # tasks here correspond to jobs
        base_cmd += '--cpus-per-task {} '.format(args.cpus)
        if args.gpus > 0:
            base_cmd += '--gres=gpu:A5000:{} '.format(args.gpus)

        # Memory requirements
        base_cmd += '--mem={}G '.format(args.mem)

        # Logging
        log_dir = self.get_log_dir()
        # Format is jobname_jobid_taskid.*
        base_cmd += '-o {} '.format(os.path.join(log_dir, '%x_%A_%a.o'))  # save stdout to file
        base_cmd += '-e {} '.format(os.path.join(log_dir, '%x_%A_%a.e'))  # save stderr to file

        # The --parsable flag causes sbatch to print the jobid to stdout. We read the
        # jobid with subprocess.check_output()
        base_cmd += '--parsable '

        if args.tasks_per_node == 1:
            base_cmd += "--array={}".format(args.tasklist)
            wrapper_filename = 'wrapper.sh'
        elif args.tasks_per_node > 1:
            list_of_tasklist_strings = split_tasklist_into_subjob_groups(args.tasklist, args.tasks_per_node)
            subjobs_filename = compute_subjobs_filename(args.jobfile)
            sfm = SubjobsFileManager(subjobs_filename)
            subjob_groupids = sfm.add_subjobs(list_of_tasklist_strings)
            tasklist = ','.join([str(id) for id in subjob_groupids])
            base_cmd += "--array={}".format(tasklist)
            wrapper_filename = 'multiwrapper.sh'
        else:
            raise RuntimeError('task_per_node must be >= 1')
        if args.max_tasks > 0:
            # set maximum number of running tasks
            base_cmd += '%{} '.format(args.max_tasks)
        else:
            base_cmd += ' '

        # Prevent Slurm from running this new job until the specified job ID is finished.
        if args.hold_jid is not None:
            base_cmd += "--depend=afterany:{} ".format(args.hold_jid)

        wrapper_script = self.wrap_tasks(args.jobfile, args)
        wrapper_file = self.save_wrapper_script(wrapper_script, args.jobname, filename=wrapper_filename)
        base_cmd += "{}".format(wrapper_file)
        return [base_cmd]
