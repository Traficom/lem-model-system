
def attempt_calibration(spec: dict):
    """Check if specification includes "calibration" trees.

    Transform regular parameters to include calibration,
    remove separate calibration parameters.
    A calibration (named "calibration") tree can be anywhere in the dict,
    but must refer to existing adjacent parameters or trees of parameters.
    """
    try:
        param_names = list(spec.keys())
    except AttributeError:
        # No calibration parameters in this branch, return up
        return
    for param_name in param_names:
        if param_name == "calibration":
            calibrate(spec, spec.pop(param_name))
        elif param_name == "scaling":
            scale(spec, spec.pop(param_name))
        else:
            # Search deeper
            attempt_calibration(spec[param_name])

def calibrate(spec: dict, calib_spec: dict):
    for param_name in calib_spec:
        try:
            spec[param_name] += calib_spec[param_name]
        except TypeError:
            # Search deeper
            calibrate(spec[param_name], calib_spec[param_name])

def scale(spec: dict, calib_spec: dict):
    for param_name in calib_spec:
        try:
            spec[param_name] *= calib_spec[param_name]
        except TypeError:
            # Search deeper
            scale(spec[param_name], calib_spec[param_name])
