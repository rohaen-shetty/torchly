# torchkit

![](torchly.png)

PyTorch Utility Package to setup training and testing pipeline for Computer Vision Tasks

## File Structure

![](treestructure.png)

Package has 5 sub-packages

### 1. data
Consists of Dataset, Dataloader functions and classes. Has a custom dataset class, along with transforms, gradcam visualization etc. 

### 2. models 
Includes two different network files, based on CIFAR-10 and MNIST. 

### 3. run
Consists of Train and Testing part of NeuralNet. Mainly 3 functions, train, test and run. Requires Model and Modelconfig to be sent as input.

### 4. torchsummary
Mainly modelsummary with Receptive Field calculated layer-wise.

### 5. utils
Consists of DataUtils and ModelUtils, which has helper functions mainly to plot and visualize data in former, & latter has model related functions.


## Features

#### Convolutions
* Normal 2d Convolutions
* Depthwise
* Dilated 
    

#### Normalization
* BatchNorm
* GroupNorm
* LayerNorm


#### Model Summary

* with layer-wise Receptive Field

#### Model utilities

###### Loss functions

* Cross Entropy Loss
* NLLoss

###### Evaluation Metrics

    * Accuracy

###### Optimizers

    * Stochastic Gradient Descent

###### LR Schedulers

    * Step LR
    * Reduce LR on Plateau
    * One Cycle Policy






#### Datasets

* MNIST
* CIFAR10



