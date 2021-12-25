from queue import Queue
from models.helper_functions import create_actions, fill_default_key_conf, get_updated_config_model, get_config
from models.sl_model import REBUFFER_INDEX, SLModel
import torch
from models.ae_trainer import train_ae
import numpy as np
from models.sl_model import REBUFFER_INDEX

class SLTrainer:
    def __init__(self, num_clients, config, helper_model):
        self.num_clients = num_clients
        self.measurements = [Queue() for _ in range(num_clients)]
        self.clean_data = Queue()
        self.prediction_model = helper_model
        self.num_actions = len(get_config()['ccs'])
        self.qoe_vec_len = len(get_config()['quality_cols']) - 2 #file_index, col_index
        if not get_config()['test']:
            self.model = SLModel(get_updated_config_model('sl', config))
        else:
            self.model = None
        self.sleep_time = fill_default_key_conf(config, 'sleep_sec')
        self.rounds_to_sleep = fill_default_key_conf(config, 'rounds_to_save')
        self.logs_file = fill_default_key_conf(config, 'logs_file')
        self.logs_path = fill_default_key_conf(config, 'logs_path')
        self.training = not get_config()['test']
        self.mapping_actions = {cc: np.arange(self.num_actions) == i for i, cc in enumerate(get_config()['ccs'])}
        print('created SLTrainer')

    def predict(self, state):
        return self.prediction_model.predict(state)

    def update(self, state):
        if not self.training:
            return
        self.measurements[state['server_id']].put(state)
        if self.measurements[state['server_id']].qsize() > 1:
            prev_state = self.measurements[state['server_id']].get()['state']
            output = torch.from_numpy(np.array(state['qoe_state']).reshape(1, -1))
            curr_cc = self.mapping_actions[state['curr_cc']]
            input = torch.from_numpy(np.append(prev_state.reshape(-1), curr_cc.reshape(-1)).reshape(1, -1))
            if self.model.scoring_type in ['ssim', 'bit_rate']:
                output = output / 10
                output[0, REBUFFER_INDEX] = 3 * np.log(1 + output[0, REBUFFER_INDEX])
            elif self.model.scoring_type == 'rebuffer':
                output[0, REBUFFER_INDEX] /= get_config()['buffer_length_coef']
                output = output[:, REBUFFER_INDEX].reshape(-1, 1)
            elif self.model.scoring_type == 'bin_rebuffer':
                output[0, REBUFFER_INDEX] /= get_config()['buffer_length_coef']
                output = self.model.discretize_output(output[0, REBUFFER_INDEX]).reshape(-1, 1)
            elif self.model.scoring_type in ['ssim_bin_rebuffer', 'bit_rate_bin_rebuffer']:
                output[0, REBUFFER_INDEX] /= get_config()['buffer_length_coef']
                output[0, REBUFFER_INDEX] = self.model.discretize_output(output[0, REBUFFER_INDEX])
                output[0, :REBUFFER_INDEX] /= 30.0
            self.clean_data.put((input, output))

    def clear(self):
        self.measurements = [Queue() for _ in range(self.num_clients)]

    def save(self):
        if self.model is not None:
            self.model.save()

    def load(self):
        self.prediction_model.load()
        print('loaded SLTrainer')
    
    def done(self):
        self.save()

    def update_helper_model(self, helper_model):
        self.prediction_model = helper_model
        self.load()


def train_sl(model, event,  f=None):
    train_ae(model, event, 'sl', f)