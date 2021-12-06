import pickle
from models.context_model import ContextModel
from sklearn.cluster import KMeans
from models.helper_functions import fill_default_key, fill_default_key_conf

class ClusterModel:
    def __init__(self, model_config):       
        self.context_model = ContextModel(model_config)
        context_layers =  context_layers = fill_default_key_conf(model_config, 'context_layers')
        self.num_clusters = fill_default_key_conf(model_config, 'num_clusters')

        if self.context_model.context_type == 'contextless':
            self.cluster_name = fill_default_key(model_config, 'cluster_name', f"clusters_{self.num_clusters}_{context_layers}")
        else:
            model_name = self.context_model.base_model.model_name
            self.context_model.load()
            self.context_model.eval()
            self.cluster_name = fill_default_key(model_config, 'cluster_name', f"clusters_{model_name}_{self.num_clusters}_{context_layers}")
        self.cluster_path = fill_default_key(model_config, 'saving_cluster_path')
        self.kmeans = KMeans(n_clusters=self.num_clusters)
        print('created cluster model')

    def load(self):
        with open(f"{self.cluster_path}{self.cluster_name}.pkl", 'rb') as f:
            self.kmeans = pickle.load(f)
        print('loaded cluster model')
    
    def save(self):
        with open(f"{self.cluster_path}{self.cluster_name}.pkl", 'wb') as f:
            pickle.dump(self.kmeans, f)

    def get_cluster_id(self, x):
        context = self.generate_context(x)
        answer = self.kmeans.predict([context])
        return answer[0]

    def fit(self, X):
        self.kmeans.fit(X)