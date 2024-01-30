import os
import json
from edf_vd import edf_vd_deadline_tampering

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

def create_jobs(tasks):
    jobs = []
    for task in tasks:
        t = 0
        while t + task['period'] < 100000.0:
            job = dict()
            job['status'] = 'not-arrived'
            job['completion'] = 0
            job['arrival-time'] = t
            job['wcet'] = task['lc-wcet']
            job['criticality'] = task['criticality']
            job['relative-deadline'] = task['relative-deadline']
            job['resource-access-timeline'] = task['resource-access-timeline']
            job['next-critical-interaction'] = 0
            job['resource-need'] = task['resource-need']
            job['dynamic-deadline-stack'] = [[job['relative-deadline'], 0]]
            jobs.append(job)
            t += task['period']
    
    jobs.append({ 'arrival-time': 100000.0 })
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
    jobs[system['next-job']]['status'] = 'ready'
    system['active-jobs'].append(jobs[system['next-job']])
    system['next-job'] += 1

def do_next_critical_action(system, resources):
    job = system['running-job']
    critical_action = job['resource-access-timeline'][job['next-critical-interaction']]
    job['next-critical-interaction'] += 1
    if critical_action[1] == '+':
        system['resources-remaining'][critical_action[2]] -= 1
        if (resources[critical_action[2]]['ceiling'][system['resources-remaining'][critical_action[2]]] != None and
            resources[critical_action[2]]['ceiling'][system['resources-remaining'][critical_action[2]]] < job['dynamic-deadline-stack'][-1][0]):
            job['dynamic-deadline-stack'].append([resources[critical_action[2]]['ceiling'][system['resources-remaining'][critical_action[2]]], critical_action[3]])
    else:
        system['resources-remaining'][critical_action[2]] += 1
        if job['dynamic-deadline-stack'][-1][1] == critical_action[3]:
            job['dynamic-deadline-stack'].pop()

def finish_running_job(system):
    system['running-job']['status'] = 'finished'
    system['active-jobs'].remove(system['running-job'])

def time_forward(system, jobs, resources):
    print('Current Time:', system['time'])
    if system['next-job'] == len(jobs):
        system['state'] = 'finished'
        return
    
    if system['running-job'] == None:
        system['time'] = jobs[system['next-job']]['arrival-time']
        activate_next_job(system, jobs)
        select_running_job(system)
        return

    if system['running-job']['next-critical-interaction'] < len(system['running-job']['resource-access-timeline']):
        next_critical_action = system['running-job']['resource-access-timeline'][system['running-job']['next-critical-interaction']]
        if system['time'] + (next_critical_action[0] - system['running-job']['completion']) < jobs[system['next-job']]['arrival-time']:
            system['time'] += next_critical_action[0] - system['running-job']['completion']
            system['running-job']['completion'] = next_critical_action[0]
            do_next_critical_action(system, resources)
            select_running_job(system)
            return
        else:
            system['running-job']['completion'] += jobs[system['next-job']]['arrival-time'] - system['time']
            system['time'] = jobs[system['next-job']]['arrival-time']
            activate_next_job(system, jobs)
            select_running_job(system)
            return
    else:
        if system['time'] + (system['running-job']['wcet'] - system['running-job']['completion']) < jobs[system['next-job']]['arrival-time']:
            system['time'] += system['running-job']['wcet'] - system['running-job']['completion']
            system['running-job']['completion'] = system['running-job']['wcet']
            finish_running_job(system)
            select_running_job(system)
            return
        else:
            system['running-job']['completion'] += jobs[system['next-job']]['arrival-time'] - system['time']
            system['time'] = jobs[system['next-job']]['arrival-time']
            activate_next_job(system, jobs)
            select_running_job(system)
            return

def run_simulation(jobs, resources):
    system = { 'state': 'running', 'time': 0.0, 'active-jobs': [], 'running-job': None, 'resources-remaining': dict(), 'next-job': 0 }
    for resource in resources:
        system['resources-remaining'][resource] = resources[resource]['units']
    
    while system['state'] == 'running':
        time_forward(system, jobs, resources)

def run_test(category, test_number, description):
    print(category, test_number, description['utilization'])
    tasks = description['tasks']
    edf_vd_deadline_tampering(tasks)
    convert_tasks(tasks, description['no-resources'])
    resources = create_resources(tasks, description['resource-units'])
    jobs = create_jobs(tasks)
    run_simulation(jobs, resources)

def run_scheduler():
    for test in os.listdir('./tests/schedulability'):
        run_test('schedulability', test[:-5], json.load(open(f'./tests/schedulability/{test}', 'r')))
    for test in os.listdir('./tests/qos'):
        run_test('qos', test[:-5], json.load(open(f'./tests/qos/{test}', 'r'))) 

if __name__ == '__main__':
    run_scheduler()