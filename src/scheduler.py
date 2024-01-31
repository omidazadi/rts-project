import os
import json
from edf_vd import edf_vd_deadline_tampering
from chart import draw_core_timeline, draw_qos

def create_resources(tasks, resource_units):
    resources = dict()
    for i in range(len(resource_units)):
        resource = i + 1
        resources[resource] = dict()
        resources[resource]['units'] = resource_units[i]
        resources[resource]['ceiling'] = dict()
        for j in range(resources[resource]['units'] + 1):
            resources[resource]['ceiling'][j] = None
            for task in tasks:
                if task['resource-need'][resource] > j:
                    if resources[resource]['ceiling'][j] == None:
                        resources[resource]['ceiling'][j] = task['relative-deadline']
                    else:
                        resources[resource]['ceiling'][j] = min(resources[resource]['ceiling'][j], task['relative-deadline'])
    return resources

def create_jobs(tasks, overrun):
    task_id, jobs = 1, []
    for task in tasks:
        t, task['no-jobs'], task['missed'], task['qos'] = 0, 0, 0, 0
        while t + task['period'] < 100000.0:
            task['no-jobs'] += 1
            job = dict()
            job['task'] = task_id
            job['status'] = 'not-arrived'
            job['completion'] = 0
            job['arrival-time'] = t
            job['finish-time'] = None
            job['lc-wcet'] = task['lc-wcet']
            if task['criticality'] == 'HC':
                job['hc-wcet'] = task['hc-wcet']
            job['criticality'] = task['criticality']
            job['real-deadline'] = task['period']
            job['relative-deadline'] = task['relative-deadline']
            job['resource-access-timeline'] = task['resource-access-timeline']
            job['next-critical-interaction'] = 0
            job['resource-need'] = task['resource-need']
            job['dynamic-deadline-stack'] = [[job['arrival-time'] + job['relative-deadline'], 0]]
            jobs.append(job)
            t += task['period']
        task_id += 1
    
    jobs.append({ 'arrival-time': 100000.0, 'finish': True })
    if overrun:
        jobs.append({ 'arrival-time': 50000.0, 'overrun': True })
    jobs = sorted(jobs, key=lambda x: x['arrival-time'])
    return jobs


def convert_tasks(tasks, no_resources):
    for task in tasks:
        task['resource-access-timeline'] = []
        for i in range(len(task['resource-access'])):
            access = task['resource-access'][i]
            task['resource-access-timeline'].append([access['begin'], '+', access['resource'], i + 1])
            task['resource-access-timeline'].append([access['end'], '-', access['resource'], i + 1])
        task['resource-access-timeline'] = sorted(task['resource-access-timeline'])

        task['resource-need'] = dict()
        for i in range(no_resources):
            resource, currently_locked = i + 1, 0
            task['resource-need'][resource] = 0
            for access in task['resource-access-timeline']:
                if access[2] == resource:
                    if access[1] == '+':
                        currently_locked += 1
                    else:
                        currently_locked -= 1
                task['resource-need'][resource] = max(task['resource-need'][resource], currently_locked)

def select_running_job(system):
    if system['running-job'] != None:
        system['running-job']['status'] = 'ready'
        system['running-job'] = None

    for job in system['active-jobs']:
        if system['running-job'] == None or job['dynamic-deadline-stack'][-1][0] < system['running-job']['dynamic-deadline-stack'][-1][0]:
            system['running-job'] = job

    if system['running-job'] != None:
        system['running-job']['status'] = 'running'

def activate_next_job(system, jobs):
    if 'status' not in jobs[system['next-job']]:
        system['next-job'] += 1
        return
    
    if system['overrun'] and jobs[system['next-job']]['criticality'] == 'LC':
        jobs[system['next-job']]['status'] = 'skipped'
        system['next-job'] += 1
        return
    
    jobs[system['next-job']]['status'] = 'ready'
    system['active-jobs'].append(jobs[system['next-job']])
    system['next-job'] += 1

def do_next_critical_action(system, resources):
    job = system['running-job']
    critical_action = job['resource-access-timeline'][job['next-critical-interaction']]
    job['next-critical-interaction'] += 1
    if critical_action[1] == '+':
        system['resources-remaining'][critical_action[2]] -= 1
        if system['resources-remaining'][critical_action[2]] < 0:
            print(system['resources-remaining'])
            raise Exception('Whaaa...') 
        if (resources[critical_action[2]]['ceiling'][system['resources-remaining'][critical_action[2]]] != None and
            system['time'] + resources[critical_action[2]]['ceiling'][system['resources-remaining'][critical_action[2]]] < job['dynamic-deadline-stack'][-1][0]):
            job['dynamic-deadline-stack'].append([system['time'] + resources[critical_action[2]]['ceiling'][system['resources-remaining'][critical_action[2]]], critical_action[3]])
    else:
        system['resources-remaining'][critical_action[2]] += 1
        if job['dynamic-deadline-stack'][-1][1] == critical_action[3]:
            job['dynamic-deadline-stack'].pop()

def finish_running_job(system):
    system['running-job']['status'] = 'finished'
    system['running-job']['finish-time'] = system['time']
    system['active-jobs'].remove(system['running-job'])

def prune_ready_lc_jobs(system):
    temp = []
    for job in system['active-jobs']:
        if job['criticality'] == 'HC':
            temp.append(job)
    system['active-jobs'] = temp

def get_wcet_running_job(system):
    if system['overrun']:
        return system['running-job']['hc-wcet']
    else:
        return system['running-job']['lc-wcet']

def time_forward(system, jobs, resources, scheduling):
    if system['next-job'] == len(jobs):
        system['state'] = 'finished'
        return
    
    if not system['overrun'] and system['next-job'] > 0 and 'overrun' in jobs[system['next-job'] - 1]:
        system['overrun'] = True
        prune_ready_lc_jobs(system)
        return
    
    if system['running-job'] == None:
        system['time'] = jobs[system['next-job']]['arrival-time']
        activate_next_job(system, jobs)
        select_running_job(system)
        return

    if system['running-job']['next-critical-interaction'] < len(system['running-job']['resource-access-timeline']):
        next_critical_action = system['running-job']['resource-access-timeline'][system['running-job']['next-critical-interaction']]
        if system['time'] + (next_critical_action[0] - system['running-job']['completion']) < jobs[system['next-job']]['arrival-time']:
            if next_critical_action[0] - system['running-job']['completion'] > 10.0:
                scheduling.append([system['running-job']['task'], [system['time'], system['time'] + next_critical_action[0] - system['running-job']['completion']]])
            system['time'] += next_critical_action[0] - system['running-job']['completion']
            system['running-job']['completion'] = next_critical_action[0]
            do_next_critical_action(system, resources)
            select_running_job(system)
            return
        else:
            if jobs[system['next-job']]['arrival-time'] - system['time'] > 10.0:
                scheduling.append([system['running-job']['task'], [system['time'], jobs[system['next-job']]['arrival-time']]])
            system['running-job']['completion'] += jobs[system['next-job']]['arrival-time'] - system['time']
            system['time'] = jobs[system['next-job']]['arrival-time']
            activate_next_job(system, jobs)
            select_running_job(system)
            return
    else:
        if system['time'] + (get_wcet_running_job(system) - system['running-job']['completion']) < jobs[system['next-job']]['arrival-time']:
            if get_wcet_running_job(system) - system['running-job']['completion'] > 10.0:
                scheduling.append([system['running-job']['task'], [system['time'], system['time'] + get_wcet_running_job(system) - system['running-job']['completion']]])
            system['time'] += get_wcet_running_job(system) - system['running-job']['completion']
            system['running-job']['completion'] = get_wcet_running_job(system)
            finish_running_job(system)
            select_running_job(system)
            return
        else:
            if jobs[system['next-job']]['arrival-time'] - system['time'] > 10.0:
                scheduling.append([system['running-job']['task'], [system['time'], jobs[system['next-job']]['arrival-time']]])
            system['running-job']['completion'] += jobs[system['next-job']]['arrival-time'] - system['time']
            system['time'] = jobs[system['next-job']]['arrival-time']
            activate_next_job(system, jobs)
            select_running_job(system)
            return

def run_simulation(jobs, resources):
    system = { 'state': 'running', 'time': 0.0, 'active-jobs': [], 'running-job': None, 'resources-remaining': dict(), 'next-job': 0, 'overrun': False }
    for resource in resources:
        system['resources-remaining'][resource] = resources[resource]['units']
    
    scheduling = []
    while system['state'] == 'running':
        time_forward(system, jobs, resources, scheduling)
    
    return scheduling

def calculate_qos(tasks, jobs):
    for job in jobs:
        if 'finish' in job or 'overrun' in job:
            continue

        if job['finish-time'] == None or job['finish-time'] > job['arrival-time'] + job['real-deadline']:
            tasks[job['task'] - 1]['missed'] += 1
            if job['finish-time'] != None and job['finish-time'] < job['arrival-time'] + 2 * job['real-deadline']:
                tasks[job['task'] - 1]['qos'] += ((job['arrival-time'] + 2 * job['real-deadline']) - job['finish-time']) / job['real-deadline']
        else:
            tasks[job['task'] - 1]['qos'] += 1

    for task in tasks:
        task['qos'] /= task['no-jobs']

def get_scheduled_and_qos(tasks, criticality):
    total, missed, qos = 0, 0, 0
    for task in tasks:
        if task['criticality'] == criticality:
            total += task['no-jobs']
            missed += task['missed']
            qos += task['qos'] * task['no-jobs']
    
    return [(total - missed) / total, qos / total]

def run_test(category, test_number, description):
    print(category, test_number, description['utilization'])
    tasks = description['tasks']
    edf_vd_deadline_tampering(tasks)
    convert_tasks(tasks, description['no-resources'])
    resources = create_resources(tasks, description['resource-units'])
    jobs = create_jobs(tasks, description['overrun'])
    scheduling = run_simulation(jobs, resources)
    calculate_qos(tasks, jobs)
    hc_stats, lc_stats = get_scheduled_and_qos(tasks, 'HC'), get_scheduled_and_qos(tasks, 'LC')
    draw_core_timeline(category, test_number, len(tasks), scheduling)
    draw_qos(category, test_number, hc_stats[0], hc_stats[1], lc_stats[0], lc_stats[1])

def run_scheduler():
    if os.path.exists('./tests/schedulability'):
        for test in os.listdir('./tests/schedulability'):
            if test.endswith('.json'):
                run_test('schedulability', test[:-5], json.load(open(f'./tests/schedulability/{test}', 'r')))
    if os.path.exists('./tests/qos'):
        for test in os.listdir('./tests/qos'):
            if test.endswith('.json'):
                run_test('qos', test[:-5], json.load(open(f'./tests/qos/{test}', 'r')))
    if os.path.exists('./tests/overrun'):
        for test in os.listdir('./tests/overrun'):
            if test.endswith('.json'):
                run_test('overrun', test[:-5], json.load(open(f'./tests/overrun/{test}', 'r')))

if __name__ == '__main__':
    run_scheduler()