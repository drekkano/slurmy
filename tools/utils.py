
import logging
log = logging.getLogger('slurmy')


## Success classes
class SuccessOutputFile:
    def __init__(self, delay = 1):
        self._delay = delay
        
    def __call__(self, config):
        import os, time
        time.sleep(self._delay)

        return os.path.isfile(config.output)

class SuccessTrigger:
    def __init__(self, success_file, failure_file):
        self._success_file = success_file
        self._failure_file = failure_file

    def __call__(self, config):
        import os, time
        while True:
            if not (os.path.isfile(self._success_file) or os.path.isfile(self._failure_file)):
                time.sleep(0.5)
                continue
            if os.path.isfile(self._success_file):
                os.remove(self._success_file)
                return True
            else:
                os.remove(self._failure_file)
                return False

## Finished classes
class FinishedTrigger:
    def __init__(self, finished_file):
        self._finished_file = finished_file

    def __call__(self, config):
        import os
        finished = os.path.isfile(self._finished_file)
        if finished: os.remove(self._finished_file)

        return finished

## Post-function classes
class LogMover:
    def __init__(self, target_path):
        self._target_path = target_path

    def __call__(self, config):
        import os
        os.system('cp {} {}'.format(config.backend.log, self._target_path))

## Functions for interactive slurmy
def _get_prompt():
    try:
        from IPython import embed
        return embed
    except ImportError:
        ## Fallback if ipython not available
        import code
        shell = code.InteractiveConsole(globals())
        return shell.interact

def get_sessions():
    from slurmy.tools import options as ops
    ## Synchronise bookkeeping with entries on disk
    ops.Main.sync_bookkeeping()
    bk = ops.Main.get_bookkeeping()
    if bk is None:
        log.debug('No bookeeping found')
        return []

    return sorted(bk.items(), key = lambda val: val[0].rsplit('_', 1)[-1])

def list_sessions():
    sessions = get_sessions()
    for name, vals in sessions:
        path = vals['path']
        timestamp = vals['timestamp']
        description = vals['description']
        print_string = ('{}:\n  path: {}\n  timestamp: {}'.format(name, path, timestamp))
        if description: print_string += '\n  description: {}'.format(description)
        print (print_string)

def load(name):
    from slurmy.tools import options as ops
    from slurmy import JobHandler
    import sys
    ## Synchronise bookkeeping with entries on disk
    ops.Main.sync_bookkeeping()
    bk = ops.Main.get_bookkeeping()
    if bk is None:
        log.error('No bookeeping found')
        return None
    python_version = sys.version_info.major
    if bk[name]['python_version'] != python_version:
        log.error('Python version "{}" of the snapshot not compatible with current version "{}"'.format(bk[name]['python_version'], python_version))
        return None
    work_dir = bk[name]['work_dir']
    jh = JobHandler(name = name, work_dir = work_dir, use_snapshot = True)

    return jh

def load_path(path):
    from slurmy import JobHandler
    jh_name = path
    jh_path = ''
    if '/' in jh_name:
        jh_path = jh_name.rsplit('/', 1)[0]
        jh_name = jh_name.rsplit('/', 1)[-1]
    jh = None
    # try:
    jh = JobHandler(name = jh_name, work_dir = jh_path, use_snapshot = True)
    # except ImportError:
    #   _log.error('Import error during pickle load, please make sure that your success class definition is in your PYTHONPATH')
    #   raise
    # except AttributeError:
    #   _log.error('')
    #   raise

    return jh

def load_latest():
    sessions = get_sessions()
    if not sessions:
        log.debug('No recorded sessions found')
        return None
    latest_session_name = sessions[-1][0]

    return load(latest_session_name)

## Prompt utils
def get_input_func():
    from sys import version_info
    input_func = None
    if version_info.major == 3:
        input_func = input
    else:
        input_func = raw_input

    return input_func

def _prompt_decision(message):
    while True:
        string = get_input_func()('{} (y/n): '.format(message))
        if string == 'y':
            return True
        elif string == 'n':
            return False
        else:
            print ('Please answer with "y" or "n"')

## Properties utils
def _get_update_property(name):
    def getter(self):
        return getattr(self, name)
    
    def setter(self, val):
        log.debug('Set attribute "{}" of class "{}" to value "{}"'.format(name, self, val))
        if getattr(self, name) != val:
            log.debug('Value changed, tag for update')
            self.update = True
        setattr(self, name, val)
        
    return property(fget = getter, fset = setter)

def set_update_properties(class_obj):
    for prop_name in class_obj._properties:
        setattr(class_obj, prop_name.strip('_'), _get_update_property(prop_name))
    setattr(class_obj, 'update', True)