import random
import json
from uunifast import generate_uunifastdiscard

def generate_period():
    period = random.gauss(5050.0, 3000.0)
    if period < 100.0:
        period = 100.0
    if period > 10000.0:
        period = 10000.0
    return period

def generate_resource_access_order(critical_sections, resource_units):
    access_order, k = [], []
    for i in range(len(resource_units)):
        for j in range(resource_units[i]):
            k.append(i + 1)
    
    if critical_sections > len(k):
        critical_sections = k
    
    for i in range(critical_sections):
        access_order.append(random.choice(k))
        k.remove(access_order[-1])
    
    return access_order

def generate_resource_access(wcet, access_order):
    resource_access = []
    xxx, total_sum = [], wcet * 0.5
    for i in range(len(access_order)):
        if i == 0 or random.random() < 0.5:
            share = random.random() * total_sum
            total_sum -= share
            xxx.append([share, 1])
        else:
            xxx[-1][1] += 1
    
    empty_space, current_l = wcet * 0.5 + total_sum, 0
    for i in range(len(xxx)):
        distance_space = random.random() * empty_space
        current_l += distance_space
        empty_space -= distance_space
        l, r = current_l, current_l + xxx[i][0]
        for j in range(xxx[i][1]):
            if j == 0:
                resource_access.append({ 'resource': access_order[-1], 'begin': l, 'end': r })
                access_order.pop()
            else:
                next_l, next_r = l + random.random() * (r - l), l + random.random() * (r - l)
                if next_l > next_r:
                    next_l, next_r = next_r, next_l
                
                l, r = next_l, next_r
                resource_access.append({ 'resource': access_order[-1], 'begin': l, 'end': r })
                access_order.pop()
        current_l += xxx[i][0]
    
    return resource_access

def generate_test():
    (utilization, no_tasks, hc_to_total_ratio, resource_unit_min, resource_unit_max,
     no_resources, task_critical_sections_min, task_critical_sections_max) = input().split(' ')
    utilization = float(utilization)
    no_tasks = int(no_tasks)
    hc_to_total_ratio = float(hc_to_total_ratio)
    resource_unit_min = int(resource_unit_min)
    resource_unit_max = int(resource_unit_max)
    no_resources = int(no_resources)
    task_critical_sections_min = int(task_critical_sections_min)
    task_critical_sections_max = int(task_critical_sections_max)

    tasks = dict()
    tasks['utilization'] = utilization
    tasks['no-tasks'] = no_tasks
    tasks['hc-to-total-ratio'] = hc_to_total_ratio
    tasks['resource-unit-min'] = resource_unit_min
    tasks['resource-unit-max'] = resource_unit_max
    tasks['no-resources'] = no_resources
    tasks['task-critical-sections_min'] = task_critical_sections_min
    tasks['task-critical-sections_max'] = task_critical_sections_max

    resource_units = [random.choice([i for i in range(resource_unit_min, resource_unit_max + 1)]) for j in range(no_resources)]
    tasks['resource-units'] = resource_units

    task_periods = [generate_period() for i in range(no_tasks)]
    task_utilizations = generate_uunifastdiscard(1, utilization, no_tasks)[0]
    task_criticality = ['HC' if random.random() < hc_to_total_ratio else 'LC' for i in range(no_tasks)]
    task_critical_sections = [random.choice(range(task_critical_sections_min, task_critical_sections_max + 1)) for i in range(no_tasks)]
    task_wcet = [task_periods[i] * task_utilizations[i] for i in range(no_tasks)]
    task_resource_access = []
    for i in range(no_tasks):
        wcet = 0
        if task_criticality[i] == 'LC':
            wcet = task_wcet[i]
        else:
            wcet = 0.8 * task_wcet[i]

        access_order = generate_resource_access_order(task_critical_sections[i], resource_units)
        task_resource_access.append(generate_resource_access(wcet, access_order))

    tasks['tasks'] = []
    for i in range(no_tasks):
        tasks['tasks'].append({ 'period': task_periods[i], 'utilization': task_utilizations[i], 'criticality': task_criticality[i], 
                               'no-critical-sections': task_critical_sections[i], 'resource-access': task_resource_access[i] })
        if tasks['tasks'][-1]['criticality'] == 'LC':
            tasks['tasks'][-1]['lc-wcet'] = task_wcet[i]
        else:
            tasks['tasks'][-1]['lc-wcet'] = 0.8 * task_wcet[i]
            tasks['tasks'][-1]['hc-wcet'] = task_wcet[i]
    
    json.dump(tasks, open(f'result.json', 'w'), indent=4)

if __name__ == '__main__':
    generate_test()