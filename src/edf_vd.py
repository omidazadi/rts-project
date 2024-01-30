def utilization_calculator(tasks, down, up):
    res = 0.0
    for task in tasks:
        if task['criticality'] == down:
            if up == 'LC':
                res += task['lc-wcet'] / task['period']
            else:
                res += task['hc-wcet'] / task['period']
    return res

def edf_vd_x(tasks):
    x = utilization_calculator(tasks, 'HC', 'LC') / (1 - utilization_calculator(tasks, 'LC', 'LC'))
    if x * utilization_calculator(tasks, 'LC', 'LC') + utilization_calculator(tasks, 'HC', 'HC') > 1:
        raise Exception('EDF-VD failed: x parameter does not meet the constraints.')
    return x

def edf_vd_deadline_tampering(tasks):
    x = edf_vd_x(tasks)
    for task in tasks:
        if task['criticality'] == 'LC':
            task['relative-deadline'] = task['period']
        else:
            task['relative-deadline'] = x * task['period']