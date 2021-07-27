import numpy as np
import matplotlib.cm as cmap
import time
import os.path
import matplotlib
import scipy
import pickle
# import brian_no_units  #import it to deactivate unit checking --> This should NOT be done for testing/debugging
import brian2 as b
from struct import unpack
from brian2 import *


# specify the location of the MNIST data
MNIST_data_path = '../sample/'


# --------------------------------------------------------------------------------
#              defining function
# --------------------------------------------------------------------------------
def get_labeled_data(picklename, bTrain=True):
    """Read input-vector (image) and target class (label, 0-9) and return
           it as list of tuples.
        """
    if os.path.isfile('%s.pickle' %picklename):
        data = pickle.load(open('%s.pickle' %picklename, 'rb'))
    else:
        # Open the images with gzip in read binary mode
        if bTrain:
            images = open(MNIST_data_path + 'train-images.idx3-ubyte', 'rb')
            labels = open(MNIST_data_path + 'train-labels.idx1-ubyte', 'rb')
        else:
            images = open(MNIST_data_path + 't10k-images.idx3-ubyte', 'rb')
            labels = open(MNIST_data_path + 't10k-labels.idx1-ubyte', 'rb')
        # Get metadata for images
        images.read(4)  # skip the magic_number
        number_of_images = unpack('>I', images.read(4))[0]
        rows = unpack('>I', images.read(4))[0]
        cols = unpack('>I', images.read(4))[0]
        # Get metadata for labels
        labels.read(4)  # skip the magic_number
        N = unpack('>I', labels.read(4))[0]

        if number_of_images != N:
            raise Exception('number of labels did not match the number of images')
        # Get the data
        x = np.zeros((N, rows, cols), dtype=np.uint8)  # Initialize numpy array
        y = np.zeros((N, 1), dtype=np.uint8)  # Initialize numpy array
        for i in range(N):
            if i % 1000 == 0:
                print("i: %i" % i)
            x[i] = [[unpack('>B', images.read(1))[0] for unused_col in range(cols)] for unused_row in range(rows)]
            y[i] = unpack('>B', labels.read(1))[0]

        data = {'x': x, 'y': y, 'rows': rows, 'cols': cols}
        pickle.dump(data, open("%s.pickle" % picklename, "wb"))
    return data


def get_matrix_from_file(fileName):
    ending = ''
    offset = len(ending) + 4
    if fileName[-4 - offset] == 'X':
        n_src = n_input
    else:
        if fileName[-3 - offset] == 'e':
            n_src = n_e
        else:
            n_src = n_i
    if fileName[-1 - offset] == 'e':
        n_tgt = n_e
    else:
        n_tgt = n_i
    readout = np.load(fileName)
    print(readout.shape, fileName)
    value_arr = np.zeros((n_src, n_tgt))
    if not readout.shape == (0,):
        value_arr[np.int32(readout[:, 0]), np.int32(readout[:, 1])] = readout[:, 2]
        print(value_arr.shape, 'This is the shape that was used')
    return value_arr


def normalize_weights():
    for connName in connections:
        if connName[1] == 'e' and connName[3] == 'e':
            connection=np.zeros((len(connections[connName].source),len(connections[connName].target)))
            for m in range(len(connections[connName].source)):
                for n in range(len(connections[connName].target)):
                    connection[m,n]=float(connections[connName].w[m,n])
            temp_conn = np.copy(connection)
            colSums = np.sum(temp_conn, axis=0)
            colFactors = weight['ee_input'] / colSums
            for j in range(n_e):  #
                connection[:, j] *= colFactors[j]


def get_2d_input_weights():
    name = 'XeAe'
    weight_matrix = np.zeros((n_input, n_e))
    n_e_sqrt = int(np.sqrt(n_e))
    n_in_sqrt = int(np.sqrt(n_input))
    num_values_col = n_e_sqrt * n_in_sqrt
    num_values_row = num_values_col
    rearranged_weights = np.zeros((num_values_col, num_values_row))
    connMatrix = np.zeros((len(XeAe_syn.source),len(XeAe_syn.target)))
    connMatrix[XeAe_syn.i[:],XeAe_syn.j[:]] = XeAe_syn.w[:]
    weight_matrix = np.copy(connMatrix)

    for i in range(n_e_sqrt):
        for j in range(n_e_sqrt):
            rearranged_weights[i * n_in_sqrt: (i + 1) * n_in_sqrt, j * n_in_sqrt: (j + 1) * n_in_sqrt] = \
                weight_matrix[:, i + j * n_e_sqrt].reshape((n_in_sqrt, n_in_sqrt))
    return rearranged_weights


def plot_2d_input_weights():
    name = 'XeAe'
    weights = get_2d_input_weights()
    fig = b.figure(fig_num, figsize=(18, 18))
    im2 = b.imshow(weights, interpolation="nearest", vmin=0, vmax=wmax_ee, cmap=cmap.get_cmap('hot_r'))
    b.colorbar(im2)
    b.title('weights of connection' + name)
    fig.canvas.draw()
    matplotlib.pyplot.pause(0.001)
    return im2, fig


def update_2d_input_weights(im, fig):
    weights = get_2d_input_weights()
    im.set_array(weights)
    fig.canvas.draw()
    matplotlib.pyplot.pause(0.001)
    return im


def plot_performance(fig_num):
    num_evaluations = int(num_examples/update_interval)
    time_steps = range(0, num_evaluations)
    performance = np.zeros(num_evaluations)
    fig = b.figure(fig_num, figsize = (5, 5))
    fig_num += 1
    ax = fig.add_subplot(111)
    im2, = ax.plot(time_steps, performance) #my_cmap
    b.ylim(ymax = 100)
    b.title('Classification performance')
    fig.canvas.draw()
    matplotlib.pyplot.pause(0.001)
    return im2, performance, fig_num, fig


def get_new_assignments(result_monitor, input_numbers):
    assignments = np.zeros(n_e)
    input_nums = np.asarray(input_numbers)
    maximum_rate = [0] * n_e
    for j in range(10):
        num_assignments = len(np.where(input_nums == j)[0])
        if num_assignments > 0:
            rate = np.sum(result_monitor[input_nums == j], axis = 0) / num_assignments
        for i in range(n_e):
            if rate[i] > maximum_rate[i]:
                maximum_rate[i] = rate[i]
                assignments[i] = j
    return assignments

def save_connections(ending):
    print ('save connections')
    for connName in save_conns:
        connMatrix= np.zeros((len(connections[connName].source),len(connections[connName].target)))
        for m in range(len(connections[connName].source)):
            for n in range(len(connections[connName].target)):
                connMatrix[m, n] = float(connections[connName].w[m, n])
#         connListSparse = ([(i,j[0],j[1]) for i in xrange(connMatrix.shape[0]) for j in zip(connMatrix.rowj[i],connMatrix.rowdata[i])])
        connListSparse = ([(i,j,connMatrix[i,j]) for i in range(connMatrix.shape[0]) for j in range(connMatrix.shape[1]) ])
        with open(data_path + 'weights/' + connName + ending+'.npy','wb') as f:
            np.save(f, connListSparse)
            f.close()
def save_theta(ending):
    print ('save theta')
    for pop_name in population_names:
        with open(data_path + 'weights/theta_' + pop_name + ending+'.npy','wb') as f:
            np.save(f, excit.theta)
            f.close()



def update_performance_plot(im, performance, current_example_num, fig):
    performance = get_current_performance(performance, current_example_num)
    im.set_ydata(performance)
    fig.canvas.draw()
    matplotlib.pyplot.show()
    return im, performance

def get_current_performance(performance, current_example_num):
    current_evaluation = int(current_example_num/update_interval)
    start_num = current_example_num - update_interval
    end_num = current_example_num
    difference = outputNumbers[start_num:end_num, 0] - input_numbers[start_num:end_num]
    correct = len(np.where(difference == 0)[0])
    performance[current_evaluation] = correct / float(update_interval) * 100
    return performance

def get_recognized_number_ranking(assignments, spike_rates):
    summed_rates = [0] * 10
    num_assignments = [0] * 10
    for i in range(10):
        num_assignments[i] = len(np.where(assignments == i)[0])
        if num_assignments[i] > 0:
            summed_rates[i] = np.sum(spike_rates[assignments == i]) / num_assignments[i]
    return np.argsort(summed_rates)[::-1]


#---------------------updated by Shouyu-------------------------------------------
def get_SynFun(contype):
    if contype == 'AeAi' or contype=='XeAe':
        return 'ge+=w'
    else:
        return 'gi+=w'

# ------------------------------------------------------------------------------
# load MNIST
# ------------------------------------------------------------------------------
start = time.time()
training = get_labeled_data(MNIST_data_path + 'training')
end = time.time()
print('time needed to load training set:', end - start)

start = time.time()
testing = get_labeled_data(MNIST_data_path + 'testing', bTrain=False)
end = time.time()
print('time needed to load test set:', end - start)

# ------------------------------------------------------------------------------
# set parameters and equations
# ------------------------------------------------------------------------------
test_mode = False

np.random.seed(0)
data_path = '../paper code/'
if test_mode:
    weight_path = data_path + 'weights/'
    num_examples = 10000 * 1
    use_testing_set = True
    do_plot_performance = False
    record_spikes = True
    ee_STDP_on = False
    update_interval = num_examples
else:
    weight_path = data_path + 'random_training/'
    num_examples = 60000 * 3
    use_testing_set = False
    do_plot_performance = True
    if num_examples <= 60000:
        record_spikes = True
    else:
        record_spikes = True
    ee_STDP_on = True

n_input = 784
n_e = 100
n_i = n_e
single_example_time = 350 * ms  #
resting_time = 150 * ms
runtime = num_examples * (single_example_time + resting_time)
if num_examples <= 10000:
    update_interval = num_examples
    weight_update_interval = 20
else:
    update_interval = 10000
    weight_update_interval = 100
if num_examples <= 60000:
    save_connections_interval = 10000
else:
    save_connections_interval = 10000
    update_interval = 10000

v_rest_e = -65. * b.mV
v_rest_i = -60. * b.mV
v_reset_e = -65. * b.mV
v_reset_i = -45. * b.mV
v_thresh_e = -52. * b.mV
v_thresh_i = -40. * b.mV
refrac_e = 5. * b.ms
refrac_i = 2. * b.ms

ending=''
weight = {}
delay = {}
input_population_names = ['X']
population_names = ['A']
input_connection_names = ['XA']
save_conns = ['XeAe']
input_conn_names = ['ee_input']
recurrent_conn_names = ['ei', 'ie']
weight['ee_input'] = 78.
delay['ee_input'] = (0 * b.ms, 10 * b.ms)
delay['ei_input'] = (0 * b.ms, 5 * b.ms)
input_intensity = 2.
start_input_intensity = input_intensity

tc_pre_ee = 20 * b.ms
tc_post_1_ee = 20 * b.ms
tc_post_2_ee = 40 * b.ms
nu_ee_pre = 0.0001  # learning rate
nu_ee_post = 0.01  # learning rate
wmax_ee = 1.0
wmin = 0
exp_ee_pre = 0.2
exp_ee_post = exp_ee_pre
STDP_offset = 0.4

if test_mode:
    scr_e = 'v = v_reset_e; timer = 0*ms'
else:
    tc_theta = 1e7 * b.ms
    theta_plus_e = 0.05 * b.mV
    scr_e = 'v = v_reset_e; theta += theta_plus_e; timer = 0*ms'
offset = 20.0 * b.mV
v_thresh_e_str = 'v>(theta - offset + v_thresh_e)'
eqs_XeAe_syn= 'w  :1'
neuron_eqs_e = '''
        dv/dt = ((v_rest_e - v) + (I_synE+I_synI) / nS) / (100*ms)  : volt (unless refractory)
        I_synE = ge * nS *         -v                           : amp 
        I_synI = gi * nS * (-100.*mV-v)                          : amp 
        dge/dt = -ge/(1.0*ms)                                   : 1 
        dgi/dt = -gi/(2.0*ms)                                  : 1  
        '''
if test_mode:
    neuron_eqs_e += '\n  theta      :volt'
else:
    neuron_eqs_e += '\n  dtheta/dt = -theta / (tc_theta)  : volt'
neuron_eqs_e += '\n  dtimer/dt = 0.1  : second'

neuron_eqs_i = '''
        dv/dt = ((v_rest_i - v) + (I_synE+I_synI) / nS) / (10*ms)  : volt (unless refractory)
        I_synE = ge * nS *         -v                           : amp 
        I_synI = gi * nS * (-85.*mV-v)                          : amp 
        dge/dt = -ge/(1.0*ms)                                   : 1 
        dgi/dt = -gi/(2.0*ms)                                  : 1 
        '''
eqs_stdp_ee = '''
                post2before                            : 1
                dpre/dt   =   -pre/(tc_pre_ee)         : 1 (clock-driven)
                dpost1/dt  = -post1/(tc_post_1_ee)     : 1 (clock-driven)
                dpost2/dt  = -post2/(tc_post_2_ee)     : 1 (clock-driven)
            '''
eqs_stdp_pre_ee = 'pre = 1.; w = clip(w-nu_ee_pre * post1,wmin,wmax_ee)'
eqs_stdp_post_ee = 'post2before = post2; w =clip(w+nu_ee_post * pre * post2before,wmin,wmax_ee); post1 = 1.; post2 = 1.'
''''''
b.ion()
fig_num = 1
neuron_groups = {}
input_groups = {}
connections = {}
stdp_methods = {}
rate_monitors = {}
spike_monitors = {}
spike_counters = {}
result_monitor = np.zeros((update_interval, n_e))

neuron_groups_e = b.NeuronGroup(n_e * len(population_names), neuron_eqs_e, threshold=v_thresh_e_str,
                                refractory=refrac_e, reset=scr_e, method='euler'
                                )
neuron_groups_i = b.NeuronGroup(n_i * len(population_names), neuron_eqs_i, threshold='v>v_thresh_i',
                                refractory=refrac_i, reset='v= v_reset_i', method ='euler'
                                )

# ------------------------------------------------------------------------------
# create network population and recurrent connections
# ------------------------------------------------------------------------------
for name in population_names:
    print('create neuron group', name)
    excit = neuron_groups_e  # .subgroup(n_e)  this function has been removed from brian2 library
    inhit = neuron_groups_i  # .subgroup(n_i)

    excit.v = v_rest_e - 40. * b.mV
    inhit.v = v_rest_i - 40. * b.mV
    if test_mode or weight_path[-8:] == 'weights/':
        excit.theta = np.load(weight_path + 'theta_' + name + ending + '.npy') * volt
    else:
        excit.theta = np.ones(n_e) * 20.0 * b.mV

    print('create recurrent connections')
    for conn_type in recurrent_conn_names:
        connName = name + conn_type[0] + name + conn_type[1]
        weightMatrix = get_matrix_from_file(weight_path + '../random_training/' + connName + ending + '.npy')
        # -----------------------updated by Shouyu------------------------
        source, target = weightMatrix.nonzero()
        print(np.count_nonzero(weightMatrix), 'non-zero values were detected for ' + connName)

        if connName == 'AeAi':
            print('Building synapses from excitatory to inhibitory layer.')
            AeAi_syn = b.Synapses(excit, inhit, 'w : 1',
                                  on_pre=get_SynFun(connName))
            AeAi_syn.connect(i=source, j=target)
            for m, n in zip(source, target):
                AeAi_syn.w[m, n] = weightMatrix[m, n]
            connections['AeAi']=AeAi_syn
        elif connName == 'AiAe':
            print('Building synapses from inhibitory to excitatory layer.')
            AiAe_syn = b.Synapses(inhit, excit, 'w : 1',
                                  on_pre=get_SynFun(connName))
            AiAe_syn.connect(i=source, j=target)
            for m, n in zip(source, target):
                AiAe_syn.w[m, n] = weightMatrix[m, n]
            connections['AiAe']=AiAe_syn
        # -----------------------updated by Shouyu------------------------
    if ee_STDP_on:
        if 'ee' in recurrent_conn_names:
            stdp_methods[name + 'e' + name + 'e'] = b.STDP(connections[name + 'e' + name + 'e'], eqs=eqs_stdp_ee,
                                                           pre=eqs_stdp_pre_ee,
                                                           post=eqs_stdp_post_ee, wmin=0., wmax=wmax_ee)

    print('create monitors for', name)
    rate_monitors_Ae = b.PopulationRateMonitor(excit)
    rate_monitors_Ai = b.PopulationRateMonitor(inhit)
    rate_monitors['Ae']=rate_monitors_Ae
    rate_monitors['Ai']=rate_monitors_Ai
    spike_counters_Ae = b.SpikeMonitor(excit, record=True).count
    spike_counters['Ae']=spike_counters_Ae
    if record_spikes:
        spike_monitors_Ae = b.SpikeMonitor(excit, record=True)
        spike_monitors_Ai = b.SpikeMonitor(inhit, record=True)
        spike_monitors['Ae']=spike_monitors_Ae
        spike_monitors['Ai']=spike_monitors_Ai
        #state_monitors_Ae = b.StateMonitor(excit,variables=True,record=True)
        #state_monitors_Ai = b.StateMonitor(inhit,variables=True,record=True)
if record_spikes:
    b.figure(fig_num)
    fig_num += 1
    b.ion()
    b.subplot(211)
    b.plot(spike_monitors_Ae.t / ms, spike_monitors_Ae.i, '.k')
    b.subplot(212)
    b.plot(spike_monitors_Ai.t / ms, spike_monitors_Ai.i, '.k')

#------------------------------------------------------------------------------
# create input population and connections from input populations
#------------------------------------------------------------------------------
pop_values = [0,0,0]
for i,name in enumerate(input_population_names):
    Xe = b.NeuronGroup(n_input,'rates :Hz', threshold='rand()<rates*dt')
    rate_monitors_Xe = b.PopulationRateMonitor(Xe)
    rate_monitors['Xe']=rate_monitors_Xe
    input_monitor = SpikeMonitor(Xe, record=True)
for name in input_connection_names:
    print ('create connections between', name[0], 'and', name[1])
    for connType in input_conn_names:
        connName = name[0] + connType[0] + name[1] + connType[1] #XeAe
        weightMatrix = get_matrix_from_file(weight_path + connName + ending + '.npy')
        # -----------------------updated by Shouyu------------------------
        source, target = weightMatrix.nonzero()
        print(np.count_nonzero(weightMatrix), 'non-zero values were detected for ' + connName)
        # -----------------------updated by Shouyu------------------------
        XeAe_syn = b.Synapses(Xe, excit,eqs_XeAe_syn, on_pre= get_SynFun(connName))
        #connections[connName].connect(input_groups[connName[0:2]], neuron_groups[connName[2:4]], weightMatrix, delay=delay[connType])
        if ee_STDP_on:
            print('create STDP for connection', name[0] + 'e' + name[1] + 'e')
            on_pre_stdp = '''
                          ge+=w
                          pre=1
                          w = clip(w-nu_ee_pre*post1,wmin,wmax_ee)
                          '''
            XeAe_syn = Synapses(Xe,excit,eqs_XeAe_syn+'\n' + eqs_stdp_ee,on_pre=on_pre_stdp,on_post=eqs_stdp_post_ee,method='euler')

        XeAe_syn.connect(i=source, j=target)
        for m, n in zip(source, target):
            XeAe_syn.w[m, n] = weightMatrix[m, n]
        XeAe_syn.delay='rand()*10*ms'
        connections['XeAe']=XeAe_syn
        #state_monitors_XA_syn = StateMonitor(XeAe_syn,['w','pre','post1','post2'],record=XeAe_syn[:,49])
        #stdp_methods[name[0]+'e'+name[1]+'e'] = b.STDP(connections[name[0]+'e'+name[1]+'e'], eqs=eqs_stdp_ee, pre = eqs_stdp_pre_ee,
        #                                               post = eqs_stdp_post_ee, wmin=0., wmax= wmax_ee)

# ------------------------------------------------------------------------------
# run the simulation and set inputs
# ------------------------------------------------------------------------------
previous_spike_count = np.zeros(n_e)
assignments = np.zeros(n_e)
input_numbers = [0] * num_examples
outputNumbers = np.zeros((num_examples, 10))
if not test_mode:
    input_weight_monitor, fig_weights = plot_2d_input_weights()
    fig_num += 1
if do_plot_performance:
    performance_monitor, performance, fig_num, fig_performance = plot_performance(fig_num)
for i, name in enumerate(input_population_names):
    Xe.rates = 0 * Hz
b.run(0 * ms)
j = 0
print('Start simulation running')
b.show()
matplotlib.pyplot.pause(0.001)
while j < (int(num_examples)):
    if test_mode:
        if use_testing_set:
            rates_input = testing['x'][j % 10000, :, :].reshape((n_input)) / 8. * input_intensity
        else:
            rates_input = training['x'][j % 60000, :, :].reshape((n_input)) / 8. * input_intensity
    else:
        normalize_weights()
        rates_input = training['x'][j % 60000, :, :].reshape((n_input)) / 8. * input_intensity
    Xe.rates = rates_input * Hz
    #     print 'run number:', j+1, 'of', int(num_examples)
    #input_monitor = SpikeMonitor(Xe, record=True)
    b.run(single_example_time, report='text')

    if j % update_interval == 0 and j > 0:
        assignments = get_new_assignments(result_monitor[:], input_numbers[j - update_interval: j])
    if j % weight_update_interval == 0 and not test_mode:
        update_2d_input_weights(input_weight_monitor, fig_weights)
        fig_weights.savefig('weight'+str(j)+'.png')
        b.show()
    if j % save_connections_interval == 0 and j > 0 and not test_mode:
        save_connections(str(j))
        save_theta(str(j))
    scope=np.copy(np.asarray(spike_monitors_Ae.count[:]))
    current_spike_count = scope - previous_spike_count
    previous_spike_count = np.copy(scope)
    if np.sum(current_spike_count) < 5:
        print('Inadequate input intensity, adjustment needed')
        print('Current spike count:', np.sum(current_spike_count))
        #print('All neuron conductance:',state_monitors_Ae.ge)
        input_intensity += 1
        if input_intensity > 20:
            plot(input_monitor.t / ms, input_monitor.i, 'k.')
            raise ValueError('Exceed maximum number')
        for i, name in enumerate(input_population_names):
            Xe.rates = 0 * Hz
        b.run(resting_time)
    else:
        result_monitor[j % update_interval, :] = current_spike_count
        if test_mode and use_testing_set:
            input_numbers[j] = testing['y'][j % 10000][0]
        else:
            input_numbers[j] = training['y'][j % 60000][0]
        outputNumbers[j, :] = get_recognized_number_ranking(assignments, result_monitor[j % update_interval, :])
        if j % 100 == 0 and j > 0:
            print('runs done:', j, 'of', int(num_examples))
        if j % update_interval == 0 and j > 0:
            if do_plot_performance:
                unused, performance = update_performance_plot(performance_monitor, performance, j, fig_performance)
                b.show()
                fig_performance.savefig('performance'+str(j)+'.png')
                print('Classification performance', performance[:int(j / float(update_interval)) + 1])
        for i, name in enumerate(input_population_names):
            Xe.rates = 0 * Hz
        b.run(resting_time)
        input_intensity = start_input_intensity
        j += 1
# ------------------------------------------------------------------------------
# save results
# ------------------------------------------------------------------------------
print('save results')
if not test_mode:
    save_theta()
if not test_mode:
    save_connections()
else:
    np.save(data_path + 'activity/resultPopVecs' + str(num_examples), result_monitor)
    np.save(data_path + 'activity/inputNumbers' + str(num_examples), input_numbers)

# ------------------------------------------------------------------------------
# plot results
# ------------------------------------------------------------------------------
if rate_monitors:
    b.figure(fig_num)
    fig_num += 1
    for i, name in enumerate(rate_monitors):
        b.subplot(len(rate_monitors), 1, i)
        b.plot(rate_monitors[name].times / b.second, rate_monitors[name].rate, '.')
        b.title('Rates of population ' + name)

if spike_monitors:
    b.figure(fig_num)
    fig_num += 1
    for i, name in enumerate(spike_monitors):
        b.subplot(len(spike_monitors), 1, i)
        b.plot(spike_monitors[name].t/ms,spike_monitors[name].i,'.k')
        b.title('Spikes of population ' + name)

if spike_counters:
    b.figure(fig_num)
    fig_num += 1
    for i, name in enumerate(spike_counters):
        b.subplot(len(spike_counters), 1, i)
        b.plot(spike_counters['Ae'].count[:])
        b.title('Spike count of population ' + name)

plot_2d_input_weights()
b.ioff()
b.show()





