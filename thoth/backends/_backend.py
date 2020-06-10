from datetime import datetime, timedelta
import os
import subprocess
import sys

from ..constants import default_logs_folder
from ..utils import update_jobindex, insert_second_to_last

class Backend:
    def __init__(self):
        self.name = 'generic_backend'
        self.header = """#!/bin/bash

"""

        self.body = """python -m thoth.worker {} {}
"""

        self.footer = ''

        self.task_id_var = r'$TASK_ID'

    def wrap_tasks(self, tasks_file, stdout=None, stderr=None):
        body = self.body.format(tasks_file, self.task_id_var)
        wrapper_script = self.header + body + self.footer
        return wrapper_script

    def save_wrapper_script(self, wrapper_script, jobname):
        scripts_dir = ".thoth/scripts/{}/".format(jobname)
        os.makedirs(scripts_dir, exist_ok=True)
        jobfile = os.path.join(scripts_dir, 'wrapper.sh')
        with open(jobfile, 'w') as file:
            file.write(wrapper_script)
        return jobfile

    def get_job_list(self, args):
        raise NotImplementedError

    def get_cancel_cmds(self, cancellations):
        raise NotImplementedError

    def get_time_delta(self, time_str):
        days, hours_minutes_seconds = time_str.split('-')
        t = datetime.strptime(hours_minutes_seconds, "%H:%M:%S")
        partial_days = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        return timedelta(days=int(days)) + partial_days

    def get_log_dir(self):
        log_dir = os.path.join(default_logs_folder, self.name)
        os.makedirs(log_dir, exist_ok=True)
        return log_dir

    def generate_tasklist(self, commands):
        ids = sorted(commands.keys())
        tasklist = ','.join(map(str, ids))
        return tasklist

    def launch(self, jobs, args, other_args):
        jobids = []

        if len(other_args) != 0:
            additional_args = ' '.join(other_args)
            jobs = [insert_second_to_last(job, additional_args) for job in jobs]

        for job in jobs:
            if not args.quiet:
                print(job)
            if not args.dry_run:
                try:
                    byte_str = subprocess.check_output(job, shell=True)
                    jobid = byte_str.decode('utf-8').split('.')[0]
                    jobids.append(jobid)
                except (subprocess.CalledProcessError, ValueError) as err:
                    print(err)
                    sys.exit()
        job_entries = [(jobid, args.jobname, args.jobfile) for jobid in jobids]
        update_jobindex(job_entries, append=True)
