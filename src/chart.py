import matplotlib.pyplot as plt
from matplotlib.colors import hsv_to_rgb

def draw_core_timeline(category, test_number, no_tasks, scheduling):
    fig, ax = plt.subplots()
    fig.set_size_inches((8, 2))
    fig.subplots_adjust(left=0.05, right=0.95, top=0.85, bottom=0.25)
    ax.set_title('Timeline of the Core')
    ax.set_xlabel('Time(s)')
    ax.set_xticks([i * 100000 / 10 for i in range(0, 11)], [i * 10 for i in range(0, 11)])
    ax.tick_params(left = False, labelleft = False)

    for segment in scheduling:
        ax.broken_barh(xranges=[(segment[1][0], segment[1][0] - segment[1][1])], 
                       yrange=(1, 1), facecolor=hsv_to_rgb(((segment[0] / no_tasks), 0.5, 1.0)))
        
    fig.savefig(f'tests/{category}/{test_number}_timeline.jpg')
    plt.close(fig)

def draw_qos(category, test_number, hc_scheduled, hc_qos, lc_scheduled, lc_qos):
    fig, ax = plt.subplots()
    fig.set_size_inches((8, 6))
    fig.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.05)
    ax.set_title('Quality of Service')
    ax.set_ylabel('Percentage')
    ax.set_xticks([1, 2], ['HC', 'LC'])

    width = 0.1
    ax.bar([1 - width], [hc_scheduled * 100], width=width, label='Scheduled', color=hsv_to_rgb((0.33, 0.5, 1.0)))
    ax.bar([1 + width], [hc_qos * 100], width=width, label='QoS', color=hsv_to_rgb((0.5, 0.5, 1.0)))
    ax.bar([2 - width], [lc_scheduled * 100], width=width, label='Scheduled', color=hsv_to_rgb((0.33, 0.5, 1.0)))
    ax.bar([2 + width], [lc_qos * 100], width=width, label='QoS', color=hsv_to_rgb((0.5, 0.5, 1.0)))
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), loc='upper right')
        
    fig.savefig(f'tests/{category}/{test_number}_qos.jpg')
    plt.close(fig)