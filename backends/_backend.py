from datetime import datetime, timedelta
from itertools import count, groupby
import os

class Backend:
    def __init__(self):
        self.name = 'generic_backend'
        self.header = """#!/bin/bash
        """

        self.body = """python -m worker {}
        """

        self.footer = """"""

        self.task_id_var = r'$TASK_ID'

    def wrap_tasks(self, tasks_file, stdout=None, stderr=None):
        body = self.body.format(tasks_file, self.task_id_var)
        wrapper_script = self.header + body + self.footer
        return wrapper_script

    def save_wrapper_script(self, wrapper_script, jobname):
        scripts_dir = ".thoth/scripts/{}/{}/".format(self.name, jobname)
        os.makedirs(scripts_dir, exist_ok=True)
        jobfile = os.path.join(scripts_dir, 'wrapper.sh')
        with open(jobfile, 'w') as file:
            file.write(wrapper_script)
        return jobfile

    def get_job_list(self, args):
        raise NotImplementedError

    def get_time_delta(self, time_str):
        days, hours_minutes_seconds = time_str.split('-')
        t = datetime.strptime(hours_minutes_seconds, "%H:%M:%S")
        partial_days = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        return timedelta(days=int(days)) + partial_days

    def get_log_dir(self):
        log_dir = ".thoth/logs/{}/".format(self.name)
        os.makedirs(log_dir, exist_ok=True)
        return log_dir

    def condense_ids(self, id_list):
        G = (list(x) for _,x in groupby(id_list, lambda x,c=count(): next(c)-x))
        return ",".join("-".join(map(str,(g[0],g[-1])[:len(g)])) for g in G)

    def expand_ids(self, tasklist):
        return [i for r in self._generate_id_ranges(tasklist) for i in r]

    def _generate_id_ranges(self, tasklist):
        task_blocks = tasklist.split(',')
        for task_block in task_blocks:
            if ':' in task_block:
                task_block, step = task_block.split(':')
                step = int(step)
            else:
                step = 1
            if '-' in task_block:
                first, last = map(int, task_block.split('-'))
            else:
                first = int(task_block)
                last = first
            yield range(first, last+1, step)