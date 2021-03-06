from torch.nn import functional as F
import cv2
import torch
import matplotlib.pyplot as plt
import numpy as np

class GradCAM():
    """ Helper Class for extracting activations and 
    registering gradients from target(intermediate) layers 
    target_layers = list of convolution layer index as shown in summary
    """
    def __init__(self, model, candidate_layers=None):
        def save_fmaps(key):
          def forward_hook(module, input, output): # this will return Input & Output of  a layer during Forward Pass
              self.fmap_pool[key] = output.detach() 
          return forward_hook

        def save_grads(key):
          def backward_hook(module, grad_in, grad_out): # this will return Input & Output of a layer during Backward Pass
              self.grad_pool[key] = grad_out[0].detach()
          return backward_hook

        self.device = next(model.parameters()).device
        self.model = model
        self.handlers = []  # a set of hook function handlers
        self.fmap_pool = {}
        self.grad_pool = {}
        self.candidate_layers = candidate_layers  # list
        for name, module in self.model.named_modules():
            if self.candidate_layers is None or name in self.candidate_layers:
                self.handlers.append(module.register_forward_hook(save_fmaps(name))) # appending I/P & O/P of a layer during forward pass
                self.handlers.append(module.register_backward_hook(save_grads(name))) # same during backward pass


    def _encode_one_hot(self, ids):
        one_hot = torch.zeros_like(self.nll).to(self.device)  # creating a one hot tensor of self.nll shape, but filled with zeros  
        one_hot.scatter_(1, ids, 1.0) # replacing ids with 1.0 at dim = 1
        return one_hot

    def forward(self, image):
        self.image_shape = image.shape[2:] # HxW
        self.nll = self.model(image)
        return self.nll.sort(dim=1, descending=True)  # ordered results


    def backward(self, ids):
        """
        Class-specific backpropagation
        """
        one_hot = self._encode_one_hot(ids)
        self.model.zero_grad()
        self.nll.backward(gradient=one_hot, retain_graph=True)

    def remove_hook(self):
        """
        Remove all the forward/backward hook functions
        """
        for handle in self.handlers:
            handle.remove()

    def _find(self, pool, target_layer):
        if target_layer in pool.keys():
            return pool[target_layer]
        else:
            raise ValueError("Invalid layer name: {}".format(target_layer))

    def generate(self, target_layer):
        fmaps = self._find(self.fmap_pool, target_layer) # get layer feature map
        grads = self._find(self.grad_pool, target_layer) # calculate gradient wrt to each pixel of that layer feature map
        weights = F.adaptive_avg_pool2d(grads, 1) # do a gap on gradient map
        
        fmap_weight = torch.mul(fmaps, weights).sum(dim=1, keepdim=True) # multiply gap(gradient map) with original layer feature map
        fmap_weight_relu = F.relu(fmap_weight) # ReLUing the previous product
        # need to capture image size duign forward pass
        gcam = F.interpolate(
            fmap_weight_relu, self.image_shape, mode="bilinear", align_corners=False
        ) # interpolating ReLUd feature map in bilinear mode

        # scale output between 0,1
        B, C, H, W = gcam.shape
        # print('gcam shape', gcam.shape)
        gcam = gcam.view(B, -1)
        gcam -= gcam.min(dim=1, keepdim=True)[0]
        gcam /= gcam.max(dim=1, keepdim=True)[0]
        gcam = gcam.view(B, C, H, W)

        return gcam



def generate_gcam(images, device, labels, model, target_layers):
  model.eval()

  # map input to device
  images = torch.stack(images).to(device)

  # set up grad cam
  gcam = GradCAM(model, target_layers)

  # forward pass
  probs, ids = gcam.forward(images)

  # outputs agaist which to compute gradients
  ids_ = torch.LongTensor(labels).view(len(images),-1).to(device)

  # backward pass
  gcam.backward(ids=ids_)
  layers = []

  for i in range(len(target_layers)):
    target_layer = target_layers[i]
    # print("Generating Grad-CAM @{}".format(target_layer))
    # Grad-CAM
    layers.append(gcam.generate(target_layer=target_layer))
    
  # remove hooks when done
  gcam.remove_hook()
  return layers, probs, ids

def plot_gcam(config, gcam_layers, images, labels, target_layers, class_names, image_size, predicted):
    c = len(images)+1
    r = len(target_layers)+2
    fig = plt.figure(figsize=(30,18))
    # fig.subplots_adjust(hspace=0.01, wspace=0.01)
    ax = plt.subplot(r, c, 1)
    ax.text(0.3,-0.5, "INPUT", fontsize=10)
    plt.axis('off')
    

    for i in range(len(target_layers)):
      target_layer = target_layers[i]
      ax = plt.subplot(r, c, c*(i+1)+1)
      ax.text(0.3,-0.5, target_layer, fontsize=10)
      plt.axis('off')

      for j in range(len(images)):
        img = np.uint8(255*unnormalize(images[j].view(image_size), config))
        if i==0:
          ax = plt.subplot(r, c, j+2)
          ax.text(0, 0.2, f"pred={class_names[predicted[j][0]]}\nactual={class_names[labels[j]]}", fontsize=10)
          plt.axis('off')
          plt.subplot(r, c, c+j+2)
          plt.imshow(img, interpolation='bilinear')
          plt.axis('off')
          plt.subplots_adjust(wspace=0, hspace=0)
          
        
        heatmap = 1-gcam_layers[i][j].cpu().numpy()[0] # reverse the color map
        heatmap = np.uint8(255 * heatmap)
        heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
        superimposed_img = cv2.resize(cv2.addWeighted(img, 0.5, heatmap, 0.5, 0), (128,128))
        plt.subplot(r, c, (i+2)*c+j+2)
        plt.imshow(superimposed_img, interpolation='bilinear')
        plt.subplots_adjust(wspace=0, hspace=0)
        
        plt.axis('off')
    plt.show()


def unnormalize(img, config):
  img = img.cpu().numpy().astype(dtype=np.float32)
  for i in range(img.shape[0]):
    img[i] = (img[i]*config.std_dev[i])+config.mean[i] # if not unnormalized then the resulting images will be dark and not visible
  return np.transpose(img, (1,2,0))
