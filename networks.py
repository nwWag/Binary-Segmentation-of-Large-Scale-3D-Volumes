import torch
import torchvision
import torch.nn as nn
import torch.optim as optim
import numpy as np
from torch.utils.data import TensorDataset, DataLoader
import torchvision.transforms as transforms
from pykdtree.kdtree import KDTree
import functools


import layers
from config import device



# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Base Network Class
class Network_Generator():
    def __init__(self, rate_learn, size_batch, size_iter, size_print_every, oj_loss, optimizer, oj_model, collate_fn=None):

        # Params +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        self._rate_learning = rate_learn
        self._size_batch = size_batch
        self._size_iter = size_iter
        self._size_print_every = size_print_every

        # (Function) Objects +++++++++++++++++++++++++++++++++++++++++++++++++++
        self._oj_model = oj_model
        self._oj_optimizer = optimizer(self._oj_model.parameters(), lr = self._rate_learning)
        self._oj_loss = oj_loss
        self._collate_fn = collate_fn

    # TODO only working with batchsize 1 currently (actual labels)
    def test(self, test_dataset, draw=True, side_len=16):
        loader_test = DataLoader(dataset=test_dataset, batch_size=self._size_batch, pin_memory=False, shuffle=True, collate_fn=self._collate_fn)
        checkpoint = torch.load("model/"+ type(self._oj_model).__name__ + "_" + str(device) + ".pt", map_location=lambda storage, loc: storage)
        self._oj_model.load_state_dict(checkpoint)
        del checkpoint  # dereference seems crucial
        torch.cuda.empty_cache()

        with torch.no_grad():
            losses_test_batch = []
            precision_test_batch = []
            recall_test_batch = []
            for batch in loader_test:
                self._oj_model.eval()
                # Makes predictions
                volume, coords, labels, actual = batch
                yhat = self._oj_model.inference(volume.to(device), coords.to(device))
                hits = torch.squeeze(yhat)
                #print("Acitvation Test", torch.sum(yhat).item())
                locs = coords[hits == 1]
                if draw:
                    to_write = locs.cpu().numpy().astype(np.short)
                    # Only each 10th as meshlab crashes otherwise
                    to_write_act = actual[::10,:].cpu().numpy().astype(np.short)
                    #mean (shape) centering
                    mean = np.array([volume.shape[2] * side_len/2, volume.shape[3] * side_len/2, volume.shape[4] * side_len/2])
                    to_write_act = to_write_act - mean
                    to_write = to_write - mean# np.mean(to_write, axis=0)

                    with open('outfile_auto.obj','w') as f:
                        for line in to_write:
                            f.write("v " + " " + str(line[0]) + " " + str(line[1]) + " " + str(line[2]) + 
                             " " + "0.5" + " " + "0.5" + " " + "1.0" + "\n")
                        for line in to_write_act:
                            f.write("v " + " " + str(line[0]) + " " + str(line[1]) + " " + str(line[2]) + 
                            " " + "0.19" + " " + "0.8" + " " + "0.19" + "\n")

                        #Corners of volume
                        f.write("v " + " " + "0"+ " " + "0" + " " + "0" + 
                            " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")

                        f.write("v " + " " + str(volume.shape[2] * side_len)+  " " + "0" + " " + "0" + 
                            " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                        
                        f.write("v " + " " + str(volume.shape[2] * side_len) +  " " + str(volume.shape[3] * side_len) + " " + "0" + 
                            " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                    
                        f.write("v " + " " + "0" +  " " + str(volume.shape[3] * side_len) + " " + "0" + 
                            " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")

                        f.write("v " + " " + "0"+ " " + "0" + " " + str(volume.shape[4] * side_len) + 
                            " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")

                        f.write("v " + " " + str(volume.shape[2] * side_len)+  " " + "0" + " " + str(volume.shape[4] * side_len) + 
                            " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                        
                        f.write("v " + " " + str(volume.shape[2] * side_len) +  " " + str(volume.shape[3] * side_len) + " " + str(volume.shape[4] * side_len)+ 
                            " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                    
                        f.write("v " + " " + "0" +  " " + str(volume.shape[3] * side_len) + " " + str(volume.shape[4] * side_len) + 
                            " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")



                kd_tree = KDTree(actual.cpu().numpy(), leafsize=16)
                dist, _ = kd_tree.query(locs.cpu().numpy(), k=1)
                union = np.sum(dist == 0)
                precision = union/locs.shape[0]
                recall = union/actual.shape[0]
                loss_test_batch = self._oj_loss(yhat, labels.to(device)).item()
                losses_test_batch.append(loss_test_batch)
                precision_test_batch.append(precision)
                recall_test_batch.append(recall)
        
        return np.mean(np.array(losses_test_batch)), np.mean(np.array(precision_test_batch)), np.mean(np.array(recall_test_batch))

    def draw_v2(self, test_dataset, side_len):
        loader_test = DataLoader(dataset=test_dataset, batch_size=self._size_batch, pin_memory=False, shuffle=True, collate_fn=self._collate_fn)
        checkpoint = torch.load("model/"+ type(self._oj_model).__name__ + "_" + str(device) + ".pt", map_location=lambda storage, loc: storage)
        self._oj_model.load_state_dict(checkpoint)
        del checkpoint  # dereference seems crucial
        torch.cuda.empty_cache()
        side_len_clean = side_len

        with torch.no_grad():
            for batch in loader_test:
                self._oj_model.eval()
                # Makes predictions ++++++++++++
                volume, coords, _, actual = batch
                # Create initial query +++++++++
                x = torch.arange(0, volume.shape[2])
                y = torch.arange(0, volume.shape[3])
                z = torch.arange(0, volume.shape[4])
                x,y,z = torch.meshgrid(x,y,z)
                query = torch.cat((torch.unsqueeze(x.reshape(-1), dim=1), torch.unsqueeze(y.reshape(-1), dim=1),  torch.unsqueeze(z.reshape(-1), dim=1)), dim=1)
                query = query.float().to(device) * side_len
                active = 1

                to_write = np.empty((0, 3))
                # Generate basic offsets
                above = torch.FloatTensor([[0,0,1]]).to(device)
                below = torch.FloatTensor([[0,0,-1]]).to(device)
                left = torch.FloatTensor([[0,1,0]]).to(device)
                right = torch.FloatTensor([[0,-1,0]]).to(device)
                behind = torch.FloatTensor([[1,0,0]]).to(device)
                before = torch.FloatTensor([[-1,0,0]]).to(device)
                # TODO catch negative values, no error, in best case network handles this
                offsets = [above, left, behind]
                side_len -= 1

                # Loop to refine grid ++++++++++
                while active > 0 and side_len >= 1:
                    yhat = self._oj_model.inference(volume.to(device), query.to(device))
                    hits = torch.squeeze(yhat)
                    #print("Acitvation Test", torch.sum(yhat).item())
                    locs = query[hits == 1]
                    to_write = np.append(to_write, locs.cpu().numpy(), axis=0)
                    # Get scaled offsets to check for neighbours
                    offsets_s = [offset * side_len for offset in offsets]

                    coords = [locs + offset for offset in offsets_s]
                    acts = [self._oj_model.inference(volume.to(device), coord.to(device)) for coord in coords]
                    masks = [act == 1 for act in acts]
                    for i, mask in enumerate(masks):
                        current_coords = locs[torch.squeeze(mask)]

                        if i == 0:
                            add = above
                        elif i ==1 :
                            add = left
                        elif  i==2:
                            add = behind

                        for i in range(side_len):
                            to_write = np.append(to_write, (current_coords + add * (i+1)).cpu().numpy(), axis=0)
                        
                    side_len -= 2
                    query = torch.empty((0,3)).to(device)
                    masks_inv = [mask.logical_not() for mask in masks]

                    for i, mask in enumerate(masks_inv):
                        current_coords = locs[torch.squeeze(mask)]

                        if i == 0:
                            add = above
                        elif i ==1 :
                            add = left
                        elif  i==2:
                            add = behind

                        query = torch.cat((query, current_coords + add), dim=0) 

                    active = query.shape[0]
                    

                

                to_write = to_write.astype(np.short)
                # Only each 5th as meshlab crashes otherwise
                to_write_act = actual[::10,:].cpu().numpy().astype(np.short)
                with open('outfile_auto.obj','w') as f:
                    for line in to_write:
                        f.write("v " + " " + str(line[0]) + " " + str(line[1]) + " " + str(line[2]) + 
                            " " + "0.0" + " " + "0.0" + " " + "0.5  " + "\n")
                    f.write("v " + " " + "0"+ " " + "0" + " " + "0" + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")

                    f.write("v " + " " + str(volume.shape[2] * side_len_clean)+  " " + "0" + " " + "0" + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                    
                    f.write("v " + " " + str(volume.shape[2] * side_len_clean) +  " " + str(volume.shape[3] * side_len_clean) + " " + "0" + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                
                    f.write("v " + " " + "0" +  " " + str(volume.shape[3] * side_len_clean) + " " + "0" + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")

                    f.write("v " + " " + "0"+ " " + "0" + " " + str(volume.shape[4] * side_len_clean) + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")

                    f.write("v " + " " + str(volume.shape[2] * side_len_clean)+  " " + "0" + " " + str(volume.shape[4] * side_len_clean) + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                    
                    f.write("v " + " " + str(volume.shape[2] * side_len_clean) +  " " + str(volume.shape[3] * side_len_clean) + " " + str(volume.shape[4] * side_len_clean)+ 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                
                    f.write("v " + " " + "0" +  " " + str(volume.shape[3] * side_len_clean) + " " + str(volume.shape[4] * side_len_clean) + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")           
        
                with open('outfile_auto_org.obj','w') as f:
                    for line in to_write_act:
                        f.write("v " + " " + str(line[0]) + " " + str(line[1]) + " " + str(line[2]) + 
                        " " + "1.0" + " " + "0.0" + " " + "0.0" + "\n")
                            #Corners of volume
                    f.write("v " + " " + "0"+ " " + "0" + " " + "0" + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")

                    f.write("v " + " " + str(volume.shape[2] * side_len_clean)+  " " + "0" + " " + "0" + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                    
                    f.write("v " + " " + str(volume.shape[2] * side_len_clean) +  " " + str(volume.shape[3] * side_len_clean) + " " + "0" + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                
                    f.write("v " + " " + "0" +  " " + str(volume.shape[3] * side_len_clean) + " " + "0" + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")

                    f.write("v " + " " + "0"+ " " + "0" + " " + str(volume.shape[4] * side_len_clean) + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")

                    f.write("v " + " " + str(volume.shape[2] * side_len_clean)+  " " + "0" + " " + str(volume.shape[4] * side_len_clean) + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                    
                    f.write("v " + " " + str(volume.shape[2] * side_len_clean) +  " " + str(volume.shape[3] * side_len_clean) + " " + str(volume.shape[4] * side_len_clean)+ 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                
                    f.write("v " + " " + "0" +  " " + str(volume.shape[3] * side_len_clean) + " " + str(volume.shape[4] * side_len_clean) + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")  
        return 0

    def draw(self, test_dataset, side_len):
        loader_test = DataLoader(dataset=test_dataset, batch_size=self._size_batch, pin_memory=False, shuffle=True, collate_fn=self._collate_fn)
        checkpoint = torch.load("model/"+ type(self._oj_model).__name__ + "_" + str(device) + ".pt", map_location=lambda storage, loc: storage)
        self._oj_model.load_state_dict(checkpoint)
        del checkpoint  # dereference seems crucial
        torch.cuda.empty_cache()
        side_len_clean = side_len

        with torch.no_grad():
            for batch in loader_test:
                self._oj_model.eval()
                # Makes predictions ++++++++++++
                volume, coords, _, actual = batch
                # Create initial query +++++++++
                x = torch.arange(0, volume.shape[2])
                y = torch.arange(0, volume.shape[3])
                z = torch.arange(0, volume.shape[4])
                x,y,z = torch.meshgrid(x,y,z)
                query = torch.cat((torch.unsqueeze(x.reshape(-1), dim=1), torch.unsqueeze(y.reshape(-1), dim=1),  torch.unsqueeze(z.reshape(-1), dim=1)), dim=1)
                query = query.float().to(device) * side_len
                active = 1

                to_write = np.empty((0, 3))
                # Generate basic offsets
                neutral = torch.FloatTensor([[0,0,0]]).to(device)
                above = torch.FloatTensor([[0,0,1]]).to(device)
                left = torch.FloatTensor([[0,1,0]]).to(device)
                behind = torch.FloatTensor([[1,0,0]]).to(device)
                # TODO catch negative values, no error, in best case network handles this
                offsets = [left, behind, left+behind, neutral+above, above+left, above+behind, above+left+behind]
                #side_len -= 1

                # Loop to refine grid ++++++++++
                while active > 0 and side_len >= 1:
                    print(active)
                    # Get scaled offsets to check for neighbours
                    offsets_s = [neutral] + [torch.relu(offset * side_len - 1) for offset in offsets]
                    coords = [query + offset for offset in offsets_s]
                    acts = [self._oj_model.inference(volume.to(device), coord.to(device)) for coord in coords]
                    masks = [act == 1 for act in acts]
                    sum_masks = functools.reduce(lambda a,b : a & b, masks)
                    sum_masks_inv = functools.reduce(lambda a,b : a.logical_not() & b.logical_not(), masks)
                    next_query_mask = torch.squeeze((sum_masks | sum_masks_inv).logical_not())
                    mask_full = torch.squeeze(sum_masks)
                    query_to_write = query[mask_full]

                    for i in range(side_len):
                        for j in range(side_len):
                            for k in range(side_len):
                                to_write = np.append(to_write, (query_to_write + left * i + above * j + behind * k).cpu().numpy(), axis=0)

                    side_len = int(side_len/2)
                    query_next = query[next_query_mask]
                    query = torch.empty((0,3)).to(device)
                    
                    for offset in [neutral] + offsets:
                        query = torch.cat((query, query_next + offset * side_len), dim=0)

                    active = query.shape[0]
                    

                

                to_write = to_write.astype(np.short)
                # Only each 5th as meshlab crashes otherwise
                to_write_act = actual[::10,:].cpu().numpy().astype(np.short)
                with open('outfile_auto.obj','w') as f:
                    for line in to_write:
                        f.write("v " + " " + str(line[0]) + " " + str(line[1]) + " " + str(line[2]) + 
                            " " + "0.0" + " " + "0.0" + " " + "0.5  " + "\n")
                    f.write("v " + " " + "0"+ " " + "0" + " " + "0" + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")

                    f.write("v " + " " + str(volume.shape[2] * side_len_clean)+  " " + "0" + " " + "0" + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                    
                    f.write("v " + " " + str(volume.shape[2] * side_len_clean) +  " " + str(volume.shape[3] * side_len_clean) + " " + "0" + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                
                    f.write("v " + " " + "0" +  " " + str(volume.shape[3] * side_len_clean) + " " + "0" + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")

                    f.write("v " + " " + "0"+ " " + "0" + " " + str(volume.shape[4] * side_len_clean) + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")

                    f.write("v " + " " + str(volume.shape[2] * side_len_clean)+  " " + "0" + " " + str(volume.shape[4] * side_len_clean) + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                    
                    f.write("v " + " " + str(volume.shape[2] * side_len_clean) +  " " + str(volume.shape[3] * side_len_clean) + " " + str(volume.shape[4] * side_len_clean)+ 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                
                    f.write("v " + " " + "0" +  " " + str(volume.shape[3] * side_len_clean) + " " + str(volume.shape[4] * side_len_clean) + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")           
        
                with open('outfile_auto_org.obj','w') as f:
                    for line in to_write_act:
                        f.write("v " + " " + str(line[0]) + " " + str(line[1]) + " " + str(line[2]) + 
                        " " + "1.0" + " " + "0.0" + " " + "0.0" + "\n")
                            #Corners of volume
                    f.write("v " + " " + "0"+ " " + "0" + " " + "0" + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")

                    f.write("v " + " " + str(volume.shape[2] * side_len_clean)+  " " + "0" + " " + "0" + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                    
                    f.write("v " + " " + str(volume.shape[2] * side_len_clean) +  " " + str(volume.shape[3] * side_len_clean) + " " + "0" + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                
                    f.write("v " + " " + "0" +  " " + str(volume.shape[3] * side_len_clean) + " " + "0" + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")

                    f.write("v " + " " + "0"+ " " + "0" + " " + str(volume.shape[4] * side_len_clean) + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")

                    f.write("v " + " " + str(volume.shape[2] * side_len_clean)+  " " + "0" + " " + str(volume.shape[4] * side_len_clean) + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                    
                    f.write("v " + " " + str(volume.shape[2] * side_len_clean) +  " " + str(volume.shape[3] * side_len_clean) + " " + str(volume.shape[4] * side_len_clean)+ 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")
                
                    f.write("v " + " " + "0" +  " " + str(volume.shape[3] * side_len_clean) + " " + str(volume.shape[4] * side_len_clean) + 
                        " " + "1.0" + " " + "0.5" + " " + "0.5" + "\n")  
        return 0

    # Validate, ignore grads
    def _val(self, loader_val, losses_val):
        with torch.no_grad():
            losses_val_batch = []
            for batch in loader_val:

                self._oj_model.eval()
                # Makes predictions
                volume, coords, labels = batch
                yhat = self._oj_model(volume.to(device), coords.to(device))

                # Computes validation loss
                loss_val_batch = self._oj_loss(yhat, labels.to(device)).item()
                losses_val_batch.append(loss_val_batch)

            loss_val = np.mean(losses_val_batch)
            losses_val.append((loss_val))
            return loss_val


    def train(self, train_dataset, val_dataset, load=False):

        # Function vars ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        loss_best = float('inf')
        losses_train = []
        losses_val = []
        loader_train = DataLoader(dataset=train_dataset, batch_size=self._size_batch, pin_memory=True, shuffle=True, collate_fn=self._collate_fn)
        loader_val = DataLoader(dataset=val_dataset, batch_size=self._size_batch, pin_memory=True, shuffle=True, collate_fn=self._collate_fn)
        if load:
            self._oj_model.load_state_dict(torch.load( "model/"+ type(self._oj_model).__name__ + "_" + str(device) + ".pt"))
            self._oj_optimizer.load_state_dict(torch.load( "optimizer/"+ type(self._oj_model).__name__ + "_" + str(device) + ".pt"))

        # Auxiliary functions ++++++++++++++++++++++++++++++++++++++++++++++++++
        # Make a training step
        def _step_train(batch):
            volume, coords, labels = batch
            self._oj_model.train()
            yhat = self._oj_model(volume.to(device), coords.to(device))
            loss_train = self._oj_loss(yhat, labels.to(device))
            loss_train.backward()
            self._oj_optimizer.step()
            self._oj_optimizer.zero_grad()
            return loss_train.item()


        # Logic ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        for _ in range(self._size_iter):

            losses_train_batch = []
            for i, batch in enumerate(loader_train):
            
                # One step of training
                loss_train_batch = _step_train(batch)
                if i % 4 == 3:
                    print("Training Loss Batch", i, loss_train_batch,flush=True)

                if i % self._size_print_every == self._size_print_every-1:
                    loss_val = self._val(loader_val, losses_val)
                    print("Validation Loss", loss_val)

                    if loss_val < loss_best:
                        loss_best = loss_val
                        torch.save(self._oj_model.state_dict(), "model/"+ type(self._oj_model).__name__ + "_" + str(device) + ".pt")
                        torch.save(self._oj_optimizer.state_dict(), "optimizer/"+ type(self._oj_model).__name__ + "_" + str(device) + ".pt")

            loss_train = np.mean(losses_train_batch)
            losses_train.append(loss_train)
            print("Training Loss Iteration", loss_train,flush=True)


class Res_Auto_3d_Model_Occu_Parallel(nn.Module):
    def __init__(self):
        super(Res_Auto_3d_Model_Occu_Parallel,self).__init__()

        self.model = nn.DataParallel(Res_Auto_3d_Model_Occu())

    def forward(self, volume, coords):
        return self.model(volume, coords)

    def bounding_box(self, volume, side_len):
        x = torch.arange(0, volume.shape[1])
        y = torch.arange(0, volume.shape[2])
        z = torch.arange(0, volume.shape[3])
        x,y,z = torch.meshgrid(x,y,z)
        query = torch.cat((torch.unsqueeze(x.reshape(-1), dim=1), torch.unsqueeze(y.reshape(-1), dim=1),  torch.unsqueeze(z.reshape(-1), dim=1)), dim=1)
        query = query.float().to(device) * side_len
        volume = torch.unsqueeze(volume, dim=1).float()
        mask = torch.squeeze(self.inference(volume, query) == 1)
        hits = query[mask]

        maxes = torch.max(hits, dim=0)[0].int()
        mines = torch.min(hits, dim=0)[0].int()
        return mines[0].item(), maxes[0].item(), mines[1].item(), maxes[1].item(), mines[2].item(), maxes[2].item()

    def inference(self, volume, coords):
        return (torch.sign(self.forward(volume, coords) - 0.95) + 1) / 2

class Res_Auto_3d_Model_Occu(nn.Module):
    def __init__(self):
        super(Res_Auto_3d_Model_Occu,self).__init__()

        self.encode = nn.Sequential(layers.Res_Block_Down_3D(1, 64, 3, 1, nn.SELU(), False),
                                    layers.Res_Block_Down_3D(64, 64, 3, 1, nn.SELU(), True),
                                    layers.Res_Block_Down_3D(64, 64, 3, 1, nn.SELU(), True),
                                    layers.Res_Block_Down_3D(64, 64, 3, 1, nn.SELU(), True),
                                    layers.Res_Block_Down_3D(64, 3, 3, 1, nn.SELU(), True))

        self.decode = nn.Sequential(layers.Res_Block_Up_Flat(180 + 3, 256, nn.SELU()),
                                    layers.Res_Block_Up_Flat(256, 256, nn.SELU()),
                                    layers.Res_Block_Up_Flat(256, 256, nn.SELU()),
                                    layers.Res_Block_Up_Flat(256, 256, nn.SELU()),
                                    layers.Res_Block_Up_Flat(256, 128, nn.SELU()),
                                    layers.Res_Block_Up_Flat(128, 1, nn.Sigmoid()))

    def forward(self, volume, coords):
        out = self.encode(volume)
        out = out.view(out.shape[0],-1)
        out = self.decode(torch.cat((torch.repeat_interleave(out, int(coords.shape[0]/volume.shape[0]), dim=0), coords), dim=1))
        return out
    
