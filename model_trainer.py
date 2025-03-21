import os
import torch
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import v_measure_score, adjusted_rand_score, normalized_mutual_info_score
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score

class ModelTrainer:
    """
    A class to manage the training and evaluation of a PyTorch model.
    Each call is just one epoch. Epoch management is done in the training loop. 

    However, this is not universal. for different datasets that return 
    different data, we should update the train and evaluate functions. 
    """

    def __init__(self, model, criterion, optimizer, model_save_dir, device='cuda'):
        """
        Initializes the ModelTrainer.

        Args:
            model (nn.Module): PyTorch model to train.
            optimizer (torch.optim.Optimizer): Optimizer to use for training.
            criterion (torch.nn.Module): Loss function to use for training.
            model_save_dir (str): Directory to save the trained model.
            device (str): Device to use for training. Default is 'cuda'.
        """
        self.model = model
        self.criterion = criterion
        self.optimizer = optimizer
        """
        At the moment we don't use scheduler, because we have multiple small datasets and 
        we want to keep track of the learning curve; if the scheduler is used, the learning
        rate will be updated automatically, and we may not be able to see the effect of learning. 
        But rather the effect of the scheduler should be more obvious. 
        """
        # self.scheduler = scheduler
        self.device = device
        self.model_save_dir = model_save_dir

    def train(self, data_loader, epoch):
        """
        Trains the model for one epoch. 

        Args:
            data_loader (DataLoader): DataLoader for the training dataset.
            epoch (int): Current epoch number.

        Returns:
            tuple: Average loss and accuracy for the training dataset.
        """
        self.model.train()
        train_loss = 0.
        train_num = len(data_loader)    # train_loader
        train_correct = 0
        train_total = 0
        for idx, (x, y) in enumerate(data_loader):
            self.optimizer.zero_grad()
            x = x.to(self.device, dtype=torch.float32)  # do forced conversion to float32, because full-set is float64
            y = y.to(self.device)
            # y = torch.tensor(y, device=self.device)

            y_hat = self.model(x)
            loss = self.criterion(y_hat, y)
            train_loss += loss.item()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(parameters=self.model.parameters(), max_norm=5, norm_type=2)
            self.optimizer.step()
            pred = self.model.predict_on_output(y_hat)
            train_total += y_hat.size(0)
            train_correct += (pred == y).sum().item()
        
        # self.scheduler.step()
        last_model_name = f"{epoch}.pt"
        torch.save(self.model.state_dict(), os.path.join(self.model_save_dir, last_model_name))
        return train_loss / train_num, train_correct / train_total

    def evaluate(self, dataloader):
        """
        Evaluates the model on a given DataLoader.

        Args:
            dataloader (DataLoader): DataLoader for the dataset to evaluate.

        Returns:
            tuple: Average loss and accuracy for the evaluation dataset.
        """
        # in fact, depending on the dataloader given, it can be train, valid, etc. 
        # but this is just for evaluation, not training. 
        self.model.eval()
        eval_loss = 0.
        eval_num = len(dataloader)    # val_loader
        eval_correct = 0
        eval_total = 0

        with torch.no_grad():
            for idx, (x, y) in enumerate(dataloader):
                x = x.to(self.device, dtype=torch.float32)
                y = y.to(self.device)
                # y = torch.tensor(y, device=self.device)

                y_hat = self.model(x)
                loss = self.criterion(y_hat, y)
                eval_loss += loss.item()

                pred = self.model.predict_on_output(y_hat)

                eval_total += y_hat.size(0)
                eval_correct += (pred == y).sum().item()
        
        return eval_loss / eval_num, eval_correct / eval_total
    


class ReconstructionTrainer:
    """
    A class to manage the training and evaluation of a PyTorch model.
    Each call is just one epoch. Epoch management is done in the training loop. 

    ReconstructionTrainer is a ModelTrainer for autoencoder training. Its evaluation only contains loss calculation, 
    while accuracy in "prediction task" is not automatically done, but either needs classifier or clusterer. 
    We don not include this at the moment. 
    """

    def __init__(self, model, criterion, optimizer, model_save_dir, device='cuda'):
        """
        Initializes the ModelTrainer.

        Args:
            model (nn.Module): PyTorch model to train.
            optimizer (torch.optim.Optimizer): Optimizer to use for training.
            criterion (torch.nn.Module): Loss function to use for training.
            model_save_dir (str): Directory to save the trained model.
            device (str): Device to use for training. Default is 'cuda'.
        """
        self.model = model
        self.criterion = criterion
        self.optimizer = optimizer
        """
        At the moment we don't use scheduler, because we have multiple small datasets and 
        we want to keep track of the learning curve; if the scheduler is used, the learning
        rate will be updated automatically, and we may not be able to see the effect of learning. 
        But rather the effect of the scheduler should be more obvious. 
        """
        # self.scheduler = scheduler
        self.device = device
        self.model_save_dir = model_save_dir

    def train(self, data_loader, epoch):
        """
        Trains the model for one epoch. 

        Args:
            data_loader (DataLoader): DataLoader for the training dataset.
            epoch (int): Current epoch number.

        Returns:
            tuple: Average loss and accuracy for the training dataset.
        """
        self.model.train()
        train_loss = 0.
        train_num = len(data_loader)    # train_loader
        train_correct = 0
        train_total = 0
        for idx, (x, y, gt_tag) in enumerate(data_loader): 
            # We still use 
            self.optimizer.zero_grad()
            x = x.to(self.device, dtype=torch.float32)  # do forced conversion to float32, because full-set is float64
            y = y.to(self.device, dtype=torch.float32)
            gt_tag = gt_tag.to(self.device)

            y_hat = self.model(x)
            loss = self.criterion(y_hat, y) # should use reconstruction loss
            train_loss += loss.item()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(parameters=self.model.parameters(), max_norm=5, norm_type=2)
            self.optimizer.step()
            # pred = self.model.predict_on_output(y_hat)
            # train_total += y_hat.size(0)
            # train_correct += (pred == y).sum().item()
        
        # self.scheduler.step()
        last_model_name = f"{epoch}.pt"
        torch.save({
            "model_state_dict": self.model.state_dict(), 
            "optimizer_state_dict": self.optimizer.state_dict(), 
        }, os.path.join(self.model_save_dir, last_model_name))

        avg_train_loss = train_loss / train_num
        avg_train_correct = 0   # train_correct / train_total, but we do not have this. 
        return avg_train_loss, avg_train_correct

    def evaluate(self, dataloader):
        """
        Evaluates the model on a given DataLoader.

        Args:
            dataloader (DataLoader): DataLoader for the dataset to evaluate.

        Returns:
            tuple: Average loss and accuracy for the evaluation dataset.
        """
        # in fact, depending on the dataloader given, it can be train, valid, etc. 
        # but this is just for evaluation, not training. 
        self.model.eval()
        eval_loss = 0.
        eval_num = len(dataloader)    # val_loader
        eval_correct = 0
        eval_total = 0

        with torch.no_grad():
            for idx, (x, y, gt_tag) in enumerate(dataloader):
                x = x.to(self.device, dtype=torch.float32)
                y = y.to(self.device, dtype=torch.float32)
                gt_tag = gt_tag.to(self.device)

                y_hat = self.model(x)
                loss = self.criterion(y_hat, y)
                eval_loss += loss.item()

                # pred = self.model.predict_on_output(y_hat)

                # eval_total += y_hat.size(0)
                # eval_correct += (pred == y).sum().item()
        avg_eval_loss = eval_loss / eval_num
        avg_eval_correct = 0   # eval_correct / eval_total, but we do not have this. 
        return avg_eval_loss, avg_eval_correct


class LinearClassifierPredictionTrainer:
    """
    A class to manage the training and evaluation of a PyTorch model.
    Each call is just one epoch. Epoch management is done in the training loop. 

    PredictionTrainer is a ModelTrainer for prediction task training. 
    It is expected to act as trainer for prediction model and 
    for linear classifier used in evaluation of autoencoder. 
    """

    def __init__(self, model_trained, model_eval, criterion, optimizer, model_save_dir, device='cuda'):
        """
        Initializes the ModelTrainer.

        Args:
            model (nn.Module): PyTorch model to train.
            optimizer (torch.optim.Optimizer): Optimizer to use for training.
            criterion (torch.nn.Module): Loss function to use for training.
            model_save_dir (str): Directory to save the trained model.
            device (str): Device to use for training. Default is 'cuda'.
        """
        self.model_trained = model_trained
        self.model_eval = model_eval
        self.criterion = criterion
        self.optimizer = optimizer
        """
        At the moment we don't use scheduler, because we have multiple small datasets and 
        we want to keep track of the learning curve; if the scheduler is used, the learning
        rate will be updated automatically, and we may not be able to see the effect of learning. 
        But rather the effect of the scheduler should be more obvious. 
        """
        # self.scheduler = scheduler
        self.device = device
        self.model_save_dir = model_save_dir

    def train(self, data_loader, epoch):
        """
        Trains the model for one epoch. 

        Args:
            data_loader (DataLoader): DataLoader for the training dataset.
            epoch (int): Current epoch number.

        Returns:
            tuple: Average loss and accuracy for the training dataset.
        """
        self.model_eval.train()
        self.model_trained.eval()
        train_loss = 0.
        train_num = len(data_loader)    # train_loader
        train_correct = 0
        train_total = 0
        for idx, (x, y, gt_tag) in enumerate(data_loader): 
            # We still use 
            self.optimizer.zero_grad()
            x = x.to(self.device, dtype=torch.float32)  # do forced conversion to float32, because full-set is float64
            y = y.to(self.device, dtype=torch.float32)
            gt_tag = gt_tag.to(self.device)

            hidrep = self.model_trained.encode(x)   # get hidden representation
            y_hat = self.model_eval(hidrep)         # use hidden representation for prediction
            loss = self.criterion(y_hat, gt_tag) # should use reconstruction loss
            train_loss += loss.item()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(parameters=self.model_eval.parameters(), max_norm=5, norm_type=2)
            self.optimizer.step()
            pred = self.model_eval.predict_on_output(y_hat)
            train_total += y_hat.size(0)
            train_correct += (pred == gt_tag).sum().item()
        
        # self.scheduler.step()
        last_model_name = f"{epoch}.pt"
        torch.save(self.model_eval.state_dict(), os.path.join(self.model_save_dir, last_model_name))

        avg_train_loss = train_loss / train_num
        avg_train_correct = train_correct / train_total   # train_correct / train_total, but we do not have this. 
        return avg_train_loss, avg_train_correct

    def evaluate(self, dataloader):
        """
        Evaluates the model on a given DataLoader.

        Args:
            dataloader (DataLoader): DataLoader for the dataset to evaluate.

        Returns:
            tuple: Average loss and accuracy for the evaluation dataset.
        """
        # in fact, depending on the dataloader given, it can be train, valid, etc. 
        # but this is just for evaluation, not training. 
        self.model_eval.eval()
        self.model_trained.eval()
        eval_loss = 0.
        eval_num = len(dataloader)    # val_loader
        eval_correct = 0
        eval_total = 0

        with torch.no_grad():
            for idx, (x, y, gt_tag) in enumerate(dataloader):
                x = x.to(self.device, dtype=torch.float32)
                y = y.to(self.device, dtype=torch.float32)
                gt_tag = gt_tag.to(self.device)

                hidrep = self.model_trained.encode(x)   # get hidden representation
                y_hat = self.model_eval(hidrep)         # use hidden representation for prediction
                loss = self.criterion(y_hat, gt_tag)
                eval_loss += loss.item()

                pred = self.model_eval.predict_on_output(y_hat)

                eval_total += y_hat.size(0)
                eval_correct += (pred == gt_tag).sum().item()
        avg_eval_loss = eval_loss / eval_num
        avg_eval_correct = eval_correct / eval_total   # eval_correct / eval_total, but we do not have this. 
        return avg_eval_loss, avg_eval_correct
    

class ClusteringTrainer: 
    """
    A class to manage the training and evaluation of a PyTorch model.
    Each call is just one epoch. Epoch management is done in the training loop. 

    DataCollectionTrainer is for collecting hidden representations and conducting clustering. 
    """

    def __init__(self, model_trained, criterion, optimizer, model_save_dir, n_clusters=2, device='cuda'):
        """
        Initializes the ModelTrainer.

        Args:
            model (nn.Module): PyTorch model to train.
            optimizer (torch.optim.Optimizer): Optimizer to use for training.
            criterion (torch.nn.Module): Loss function to use for training.
            model_save_dir (str): Directory to save the trained model.
            device (str): Device to use for training. Default is 'cuda'.
        """
        self.model_trained = model_trained
        self.criterion = criterion
        self.optimizer = optimizer
        """
        At the moment we don't use scheduler, because we have multiple small datasets and 
        we want to keep track of the learning curve; if the scheduler is used, the learning
        rate will be updated automatically, and we may not be able to see the effect of learning. 
        But rather the effect of the scheduler should be more obvious. 
        """
        # self.scheduler = scheduler
        self.device = device
        self.model_save_dir = model_save_dir

        self.n_clusters = n_clusters

    def train(self, data_loader, epoch):
        raise NotImplementedError("ClusteringTrainer does not have training function.")

    def evaluate(self, dataloader):
        """
        Evaluates the model on a given DataLoader.

        Args:
            dataloader (DataLoader): DataLoader for the dataset to evaluate.

        Returns:
            tuple: Average loss and accuracy for the evaluation dataset.

        NOTE: this includes KMeans and LogisticRegression for evaluation. 
        """
        # in fact, depending on the dataloader given, it can be train, valid, etc. 
        # but this is just for evaluation, not training. 
        self.model_trained.eval()
        all_hidrep = []            # Store all hidden representations
        all_gt_tags = []           # Store all ground-truth tags for evaluation

        with torch.no_grad():
            for idx, (x, y, gt_tag) in enumerate(dataloader):
                x = x.to(self.device, dtype=torch.float32)
                gt_tag = gt_tag.cpu().numpy()  # Ground-truth tags

                hidrep = self.model_trained.encode(x).squeeze().cpu().numpy()   # get hidden representation
                all_hidrep.append(hidrep)
                all_gt_tags.append(gt_tag)

        # Combine all hidden representations and ground-truth tags
        all_hidrep = np.concatenate(all_hidrep, axis=0)
        all_gt_tags = np.concatenate(all_gt_tags, axis=0)

        # Apply KMeans clustering
        kmeans = KMeans(n_clusters=self.n_clusters, random_state=42)
        predicted_labels = kmeans.fit_predict(all_hidrep)

        # Calculate clustering metrics
        v_measure = v_measure_score(all_gt_tags, predicted_labels)
        ari = adjusted_rand_score(all_gt_tags, predicted_labels)
        nmi = normalized_mutual_info_score(all_gt_tags, predicted_labels)


        # Apply Logistic Regression for evaluation
        # Assume hidrep is of shape (number, 256), and y contains labels (0, 1, 2, 3).
        # Split data into training and testing sets.
        X_train, X_test, y_train, y_test = train_test_split(all_hidrep, all_gt_tags, test_size=0.3, random_state=42)

        # Scale the features using StandardScaler.
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)

        # Initialize Logistic Regression with appropriate parameters.
        clf = LogisticRegression(max_iter=1000, random_state=42, solver='lbfgs')

        # Train the classifier.
        clf.fit(X_train, y_train)

        # Make predictions.
        y_pred = clf.predict(X_test)

        # Evaluate the model.
        acc = accuracy_score(y_test, y_pred)

        return {"v_measure": v_measure, "ari": ari, "nmi": nmi}, {"acc": acc, "report": classification_report(y_test, y_pred)}