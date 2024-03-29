# -*- coding: utf-8 -*-
"""Colorisation

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Qt3mBfZFxNf3vIe63yMGTj7mVIeN6Ltw
"""

data_path = ''

# Commented out IPython magic to ensure Python compatibility.
import numpy as np
import matplotlib.pyplot as plt
# %matplotlib inline
from skimage.color import lab2rgb, rgb2lab, rgb2gray
from skimage import io
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
from torchvision import datasets, transforms
import os, shutil, time

use_gpu = torch.cuda.is_available()

class ColorizationNet(nn.Module):
  def __init__(self, input_size=128):
    super(ColorizationNet, self).__init__()
    MIDLEVEL_FEATURE_SIZE = 128

    ## First half is ResNet
    resnet = models.resnet18(num_classes=365) 
    resnet.conv1.weight = nn.Parameter(resnet.conv1.weight.sum(dim=1).unsqueeze(1)) 
    self.midlevel_resnet = nn.Sequential(*list(resnet.children())[0:6])

    ## Second half
    self.upsample = nn.Sequential(     
      nn.Conv2d(MIDLEVEL_FEATURE_SIZE, 128, kernel_size=3, stride=1, padding=1),
      nn.BatchNorm2d(128),
      nn.ReLU(),
      nn.Upsample(scale_factor=2),
      nn.Conv2d(128, 64, kernel_size=3, stride=1, padding=1),
      nn.BatchNorm2d(64),
      nn.ReLU(),
      nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1),
      nn.BatchNorm2d(64),
      nn.ReLU(),
      nn.Upsample(scale_factor=2),
      nn.Conv2d(64, 32, kernel_size=3, stride=1, padding=1),
      nn.BatchNorm2d(32),
      nn.ReLU(),
      nn.Conv2d(32, 2, kernel_size=3, stride=1, padding=1),
      nn.Upsample(scale_factor=2)
    )

  def forward(self, input):

    midlevel_features = self.midlevel_resnet(input)
    output = self.upsample(midlevel_features)
    return output

model = ColorizationNet()

criterion = nn.MSELoss()

optimizer = torch.optim.Adam(model.parameters(), lr=1e-2, weight_decay=0.0)

class GrayscaleImageFolder(datasets.ImageFolder):
  '''Custom images folder, which converts images to grayscale before loading'''
  def __getitem__(self, index):
    path, target = self.imgs[index]
    img = self.loader(path)
    if self.transform is not None:
      img_original = self.transform(img)
      img_original = np.asarray(img_original)
      img_lab = rgb2lab(img_original)
      img_lab = (img_lab + 128) / 255
      img_ab = img_lab[:, :, 1:3]
      img_ab = torch.from_numpy(img_ab.transpose((2, 0, 1))).float()
      img_original = rgb2gray(img_original)
      img_original = torch.from_numpy(img_original).unsqueeze(0).float()
    if self.target_transform is not None:
      target = self.target_transform(target)
    return img_original, img_ab, target

train_transforms = transforms.Compose([transforms.RandomResizedCrop(224), transforms.RandomHorizontalFlip()])
train_imagefolder = GrayscaleImageFolder(data_path+'images/train', train_transforms)
train_loader = torch.utils.data.DataLoader(train_imagefolder, batch_size=64, shuffle=True)

val_transforms = transforms.Compose([transforms.Resize(256), transforms.CenterCrop(224)])
val_imagefolder = GrayscaleImageFolder(data_path+'images/val' , val_transforms)
val_loader = torch.utils.data.DataLoader(val_imagefolder, batch_size=64, shuffle=False)

class AverageMeter(object):
  def __init__(self):
    self.reset()
  def reset(self):
    self.val, self.avg, self.sum, self.count = 0, 0, 0, 0
  def update(self, val, n=1):
    self.val = val
    self.sum += val * n
    self.count += n
    self.avg = self.sum / self.count

def to_rgb(grayscale_input, ab_input, save_path=None, save_name=None):
  plt.clf()
  color_image = torch.cat((grayscale_input, ab_input), 0).numpy()
  color_image = color_image.transpose((1, 2, 0))
  color_image[:, :, 0:1] = color_image[:, :, 0:1] * 100
  color_image[:, :, 1:3] = color_image[:, :, 1:3] * 255 - 128   
  color_image = lab2rgb(color_image.astype(np.float64))
  grayscale_input = grayscale_input.squeeze().numpy()
  if save_path is not None and save_name is not None: 
    plt.imsave(arr=grayscale_input, fname='{}{}'.format(save_path['grayscale'], save_name), cmap='gray')
    plt.imsave(arr=color_image, fname='{}{}'.format(save_path['colorized'], save_name))

def validate(val_loader, model, criterion, save_images, epoch):
  model.eval()

  losses = AverageMeter()

  already_saved_images = False
  for i, (input_gray, input_ab, target) in enumerate(val_loader):
    data_time.update(time.time() - end)

    if use_gpu: input_gray, input_ab, target = input_gray.cuda(), input_ab.cuda(), target.cuda()

    output_ab = model(input_gray)
    loss = criterion(output_ab, input_ab)
    losses.update(loss.item(), input_gray.size(0))

    if save_images and not already_saved_images:
      already_saved_images = True
      for j in range(min(len(output_ab), 10)):
        save_path = {'grayscale': data_path+'outputs/gray/', 'colorized': data_path+'outputs/color/'}
        save_name = 'img-{}-epoch-{}.jpg'.format(i * val_loader.batch_size + j, epoch)
        to_rgb(input_gray[j].cpu(), ab_input=output_ab[j].detach().cpu(), save_path=save_path, save_name=save_name)

    batch_time.update(time.time() - end)
    end = time.time()

    if i % 25 == 0:
      print('Validate: [{0}/{1}]\t'
            'Loss {loss.val:.4f} ({loss.avg:.4f})\t'.format(
             i, len(val_loader), loss=losses))

  return losses.avg

def train(train_loader, model, criterion, optimizer, epoch):
  print('Starting training epoch {}'.format(epoch))
  model.train()
  
  losses = AverageMeter()

  for i, (input_gray, input_ab, target) in enumerate(train_loader):
    
    if use_gpu: 
      input_gray, input_ab, target = input_gray.cuda(), input_ab.cuda(), target.cuda()

    output_ab = model(input_gray) 
    loss = criterion(output_ab, input_ab) 
    losses.update(loss.item(), input_gray.size(0))

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    if i % 25 == 0:
      print('Epoch: [{0}][{1}/{2}]\t'
            'Loss {loss.val:.4f} ({loss.avg:.4f})\t'.format(
              epoch, i, len(train_loader), loss=losses)) 

  print('Finished training epoch {}'.format(epoch))

if use_gpu: 
  criterion = criterion.cuda()
  model = model.cuda()

os.makedirs(data_path+'outputs/color', exist_ok=True)
os.makedirs(data_path+'outputs/gray', exist_ok=True)
os.makedirs(data_path+'checkpoints', exist_ok=True)
save_images = True
best_losses = 1e10
epochs = 100

for epoch in range(epochs):
  train(train_loader, model, criterion, optimizer, epoch)
  with torch.no_grad():
    losses = validate(val_loader, model, criterion, save_images, epoch)
  if losses < best_losses:
    best_losses = losses
    torch.save(model.state_dict(), data_path+'checkpoints/model-epoch-{}-losses-{:.3f}.pth'.format(epoch+1,losses))

losses = validate(val_loader, model, criterion, save_images, epoch)