# coding=utf-8


import os
import math
import shutil
from datetime import datetime
import json5
from curLine_file import curLine

class Object:
    """
    @DynamicAttrs
    """
    pass


def parse(config_file, host_name, mode):
    root = os.path.dirname(config_file) # os.path.join(,"data")  # __parent__ in config is a relative path
    config_group = _load_param('', config_file)
    if type(config_group) is dict:
        config_group = [config_group]
    configs = []
    for config in config_group:
        try:
            choice = config.pop('__iter__')
            assert len(choice) == 1, 'only support iterating over 1 variable'
            key, values = next(iter(choice.items()))
        except KeyError:
            key, value = config.popitem()
            values = [value]
        for value in values:
            config[key] = value
            repeat = config.get('__repeat__', 1)
            for index in range(repeat):
                config_ = config.copy()
                config_['__index__'] = index
                if repeat > 1:
                    config_['name'] += '-' + str(index)
                args = _parse_args(root, config_, host_name, mode)
                configs.append((args, config_))
    return configs


def _parse_args(root, config, host_name, mode):
    args = Object()
    assert type(config) is dict
    parents = config.get('__parents__', [])
    for parent in parents:
        parent = _load_param(root, parent)
        assert type(parent) is dict, 'only top-level configs can be a sequence'
        _add_param(args, parent)
    args.output_dir = args.output_dir.replace("host_name", host_name)
    args.data_dir = args.data_dir.replace("host_name", host_name)
    # print(curLine(), "args.data_dir:%s, args.output_dir:%s" % (args.data_dir, args.output_dir))
    _add_param(args, config)
    _post_process(args, mode)
    return args


def _add_param(args, x: dict):
    for k, v in x.items():
        if type(v) is dict:
            _add_param(args, v)
        else:
            k = _validate_param(k)
            if hasattr(args, k):
                previous_type = type(getattr(args, k))
                current_type = type(v)
                assert previous_type is current_type or (isinstance(None, previous_type)) or \
                    (previous_type is float and current_type is int), \
                    f'param "{k}" of type {previous_type} can not be overwritten by type {current_type}'
            setattr(args, k, v)


def _load_param(root, file_name: str):
    file = os.path.join(root, file_name)
    if not file.endswith('.json5'):
        file += '.json5'
    with open(file) as f:
        config = json5.load(f)
        return config


def _post_process(args: Object, mode: str):
    # if not args.output_dir.startswith('models'):
    #     args.output_dir = os.path.join('models', args.output_dir)
    os.makedirs(args.output_dir, exist_ok=True)
    if not args.name:
        args.name = str(datetime.now())
    args.summary_dir = os.path.join(args.output_dir, args.name)
    if mode.lower() == "train": #  清空模型目录
        if os.path.exists(args.summary_dir):
            shutil.rmtree(args.summary_dir)
        os.makedirs(args.summary_dir)
    data_config_file = os.path.join(args.output_dir, 'data_config.json5')
    if os.path.exists(data_config_file):
        with open(data_config_file) as f:
            config = json5.load(f)
            for k, v in config.items():
                args_v = "none"
                if hasattr(args, k):
                    args_v = getattr(args, k)
                if args_v != v:
                    print(curLine(),"wrong for config: args.%s=%s, not equal to %s" % (k, args_v, v))
                    print('ERROR: Data configurations are different. Please use another output_dir or '
                          'remove the older one manually.')
                    exit()
    else:
        with open(data_config_file, 'w') as f:
            keys = ['data_dir', 'min_df', 'max_vocab', 'max_len', 'min_len', 'lower_case',
                    'pretrained_embeddings', 'embedding_mode']
            json5.dump({k: getattr(args, k) for k in keys}, f)
    args.metric = args.metric.lower()
    args.watch_metrics = [m.lower() for m in args.watch_metrics]
    if args.metric not in args.watch_metrics:
        args.watch_metrics.append(args.metric)
    assert args.pretrained_embeddings, 'pretrained embeddings must be provided.'

    def samples2steps(n):
        return int(math.ceil(n / args.batch_size))

    if not hasattr(args, 'log_per_updates'):
        args.log_per_updates = samples2steps(args.log_per_samples)
    if not hasattr(args, 'eval_per_updates'):
        args.eval_per_updates = samples2steps(args.eval_per_samples)
    if not hasattr(args, 'eval_per_updates_warmup'):
        args.eval_per_updates_warmup = samples2steps(args.eval_per_samples_warmup)
    if not hasattr(args, 'eval_warmup_steps'):
        args.eval_warmup_steps = samples2steps(args.eval_warmup_samples)
    if not hasattr(args, 'min_steps'):
        args.min_steps = samples2steps(args.min_samples)
    if not hasattr(args, 'early_stopping'):
        args.early_stopping = samples2steps(args.tolerance_samples)
    if not hasattr(args, 'lr_warmup_steps'):
        args.lr_warmup_steps = samples2steps(args.lr_warmup_samples)
    if not hasattr(args, 'lr_decay_steps'):
        args.lr_decay_steps = samples2steps(args.lr_decay_samples)


def validate_params(args):
    """validate params after interface initialization"""
    assert args.num_classes == 2 or ('f1' not in args.watch_metrics and 'auc' not in args.watch_metrics), \
        f'F1 and AUC are only valid for 2 classes.'
    assert args.num_classes == 2 or 'ranking' not in args.watch_metrics, \
        f'ranking metrics are only valid for 2 classes.'
    assert args.num_vocab > 0


def _validate_param(name):
    name = name.replace('-', '_')
    if not str.isidentifier(name):
        raise ValueError(f'Invalid param name: {name}')
    return name
