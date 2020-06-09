import argparse
import subprocess
import sys

def launch_cancel_proc(cmd, args):
    """Print the qdel command and launch a subprocess to execute it"""
    print(cmd)
    if not args.dry_run:
        try:
            subprocess.call(cmd, shell=True)
        except (subprocess.CalledProcessError, ValueError) as err:
            print(err)
            sys.exit()


def cancel(args):
    """Parse the jobs/tasks to cancel and send the appropriate commands to the cluster"""

    cmd = "qdel {} ".format(args.jobid)
    if args.tasklist is not None:
        cmd += "-t {taskblock}"

    if args.tasklist is None:
        yes_or_no = input('Are you sure you want to cancel all tasks for this job? (y/[n])\n> ')
        if yes_or_no in ['y','yes','Y',"YES"]:
            launch_cancel_proc(cmd, args)
        else:
            if yes_or_no not in ['n','no','N',"NO",'']:
                print('Unable to process response "{}"'.format(yes_or_no))
            print('Job cancellation aborted.')
    else:
        taskblocks = args.tasklist.split(',')
        for taskblock in taskblocks:
            launch_cancel_proc(cmd.format(taskblock=taskblock), args)
