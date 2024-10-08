from collections import OrderedDict
import os
from warnings import warn

from .utils import load_jobfile, save_jobfile
from .constants import SEP, WSEP, FLAG_ON, FLAG_OFF
from .history import add_new_history_entry

def meta_launch(args):
    base_cmd = args.command

    if args.arg_mode == 'argparse':
        VAR_SEP = ' '
    elif args.arg_mode == 'hydra':
        VAR_SEP = '='
    else:
        raise NotImplementedError(f'Unknown arg mode: {args.arg_mode}')

    if args.arg is not None:
        variables = OrderedDict({arglist[0]: arglist[1:] for arglist in args.arg})
    else:
        variables = OrderedDict()

    if args.pos_arg is not None:
        pos_variables = args.pos_arg
    else:
        pos_variables = []
    
    if args.unique_arg is not None:
        unique_variables = [(arglist[0], arglist[1:]) for arglist in args.unique_arg]
    else:
        unique_variables = []

    if args.flag is not None:
        flag_variables = args.flag
    else:
        flag_variables = []

    base_cmd_args = list(variables.keys())

    cmd_prefix_list = [base_cmd]

    if args.tag == '':
        raise ValueError("+tag cannot be an empty string")

    if args.tag is not None:
        cmd_suffix_list = ['']
        if args.tag_args is None:
            args.tag_args = base_cmd_args
        else:
            for tag_arg in args.tag_args:
                if tag_arg not in base_cmd_args:
                    warn(RuntimeWarning("{} is not a command arg: {}".format(tag_arg,
                        base_cmd_args)))


    # Positional arguments
    for value_list in pos_variables:
        cmd_prefix_list = [prefix + ' {}' for prefix in cmd_prefix_list]
        cmd_prefix_list = [prefix.format(v) for v in value_list for prefix in cmd_prefix_list]
        if args.tag is not None:
            value_slot = WSEP + '{}'
            cmd_suffix_list = [
                suffix + value_slot for suffix in cmd_suffix_list
            ]
            cmd_suffix_list = [
                suffix.format(v) for v in value_list for suffix in cmd_suffix_list
            ]

    # Optional arguments
    for key, value_list in variables.items():
        cmd_prefix_list = [prefix + ' ' + key for prefix in cmd_prefix_list]
        if len(value_list) > 0:
            cmd_prefix_list = [prefix + VAR_SEP + '{}' for prefix in cmd_prefix_list]
            cmd_prefix_list = [prefix.format(v) for v in value_list for prefix in cmd_prefix_list]
        if args.tag is not None:
            if key in args.tag_args:
                value_slot = SEP + '{}' if len(value_list) > 0 else ''
                keyname = key.replace('_', '').replace('-', '').replace('=','_').replace('/','.')
                cmd_suffix_list = [
                    suffix + WSEP + keyname + value_slot for suffix in cmd_suffix_list
                ]
                if len(value_list) > 0:
                    cmd_suffix_list = [
                        suffix.format(v) for v in value_list for suffix in cmd_suffix_list
                    ]
            else:
                cmd_suffix_list = [suffix for v in value_list for suffix in cmd_suffix_list]
                
    # Unique arguments
    if len(unique_variables) > 0:
        for unique_var in unique_variables:
            n_unique_values = len(unique_var[1])
            if n_unique_values > 0:
                if len(cmd_prefix_list) % n_unique_values != 0:
                    warn("Number of unique variables must to able to be sequentially assigned to the other commands")
                
        for i, cmd_prefix in enumerate(cmd_prefix_list):
            unique_arg = unique_variables[i % len(unique_variables)]
            k = unique_arg[0]
            v = unique_arg[1][i % len(unique_arg[1])]
            
            cmd_prefix_list[i] = cmd_prefix + ' ' + k
            if len(v) > 0:
                cmd_prefix_list[i] = cmd_prefix_list[i] + VAR_SEP + f"{v}"

            # TODO: this doesn't handle tag

    # Flag/Boolean arguments
    for flag in flag_variables:
        cmd_prefix_list = [prefix + ' {}' for prefix in cmd_prefix_list] + cmd_prefix_list
        cmd_prefix_list = [
            prefix.format(flag) if '{}' in prefix else prefix
            for prefix in cmd_prefix_list
        ]
        if args.tag is not None:
            cmd_suffix_list = [
                suffix + '{}' for suffix in cmd_suffix_list
            ]
            cmd_suffix_list = [
                suffix.format(WSEP + s + flag.replace(FLAG_OFF, '').replace(FLAG_ON, ''))
                for s in [FLAG_ON, FLAG_OFF]
                for suffix in cmd_suffix_list
            ]

    jobfile_path = args.jobfile.format(jobname=args.jobname)
    os.makedirs(os.path.dirname(jobfile_path), exist_ok=True)

    if args.append:
        cmds, tags = load_jobfile(jobfile_path)
        start_jobid = max(cmds.keys()) + 1
        jobs = {i: (cmds[i], tags[i]) for i in cmds.keys()}
    else:
        jobs = dict()
        start_jobid = 1

    if args.tag is not None:
        if args.no_tag_number:
            tag_list = [args.jobname + suffix for suffix in cmd_suffix_list]
        else:
            n_digits = len(str(start_jobid + len(cmd_suffix_list) - 1))
            tag_number_format = '{{:0{0}d}}'.format(n_digits)
            tag_list = [
                args.jobname + SEP + tag_number_format.format(i) + suffix
                for (i, suffix) in enumerate(cmd_suffix_list, start_jobid)
            ]

        cmd_prefix_list = [
            (prefix + ' ' + args.tag + VAR_SEP + suffix)
            for (prefix, suffix) in zip(cmd_prefix_list, tag_list)
        ]
    else:
        tag_list = [""] * len(cmd_prefix_list)

    for i, (cmd, tag) in enumerate(zip(cmd_prefix_list, tag_list), start_jobid):
        if not args.quiet:
            print(cmd)
        jobs[i] = (cmd,tag)

    save_jobfile(jobs, jobfile_path, args.tag)
    add_new_history_entry(jobname=args.jobname, dry_run=False)
