import argparse
import sys
import os
from os import path
import json
import random
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim import lr_scheduler
import numpy as np
import torchvision
from torchvision import datasets, models, transforms
import matplotlib.pyplot as plt
import time
import copy
from collections import namedtuple
from sklearn.metrics import multilabel_confusion_matrix
from collections import namedtuple

def get_input_size(m):
    return 299 if m == 'inception_v3' else 256

def determine_inception(m):
    return True if m == 'inception_v3' else False

def get_model(m, num_classes, pretrained):
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    if 'resnet18' == max:
        model = models.resnet18(pretrained=pretrained)
        model.fc = nn.Linear(model.fc.in_features, num_classes)
    elif 'resnet152' == m:
        model = models.resnet152(pretrained=pretrained)
        model.fc = nn.Linear(model.fc.in_features, num_classes)
    elif 'alexnet' == m:
        model = models.alexnet(pretrained=pretrained)
        model.classifier[6] = nn.Linear(4096, num_classes)
    elif 'vgg19_bn' == m:
        model = models.vgg19_bn(pretrained=pretrained)
        model.classifier[6] = nn.Linear(model.classifier[6].in_features, num_classes)
    elif 'squeezenet1_1' == m:
        model = models.squeezenet1_1(pretrained=pretrained)
        model.classifier[1] = nn.Conv2d(512, num_classes, kernel_size=(1,1), stride=(1,1))
        model.num_classes = num_classes
    elif 'densenet201' == m:
        model = models.densenet201(pretrained=pretrained)
        model.classifier = nn.Linear(model.classifier.in_features, num_classes)
    elif 'googlenet' == m:
        model = models.googlenet(pretrained=pretrained)
        model.fc = nn.Linear(model.fc.in_features, num_classes)
    elif 'shufflenet_v2_x0_5' == m:
        model = models.shufflenet_v2_x0_5(pretrained=pretrained)
        model.fc = nn.Linear(model.fc.in_features, num_classes)
    elif 'mobilenet_v2' == m:
        model = models.mobilenet_v2(pretrained=pretrained)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    elif 'resnext101_32x8d' == m:
        model = models.resnext101_32x8d(pretrained=pretrained)
        model.fc = nn.Linear(model.fc.in_features, num_classes)
    else:
        model = models.inception_v3(pretrained=pretrained)
        model.AuxLogits.fc = nn.Linear(model.AuxLogits.fc.in_features, num_classes)
        model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model.to(device)

def get_criterion():
    return nn.CrossEntropyLoss()

def get_optimizer(model, params):
    return optim.SGD(model.parameters(), **params)

def get_scheduler(optimizer, params):
    return lr_scheduler.StepLR(optimizer, **params)

def get_dataloaders(data_dir, input_size, batch_size, num_workers):
    data_transforms = {
        'train': transforms.Compose([
            transforms.Resize(input_size),
            transforms.CenterCrop(input_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ]),
        'test': transforms.Compose([
            transforms.Resize(input_size),
            transforms.CenterCrop(input_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ]),
        'valid': transforms.Compose([
            transforms.Resize(input_size),
            transforms.CenterCrop(input_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
    }

    shuffles = {
        'train': True,
        'test': True,
        'valid': False
    }

    samples = ['train', 'test', 'valid']
    image_datasets = { x: datasets.ImageFolder(os.path.join(data_dir, x), transform=data_transforms[x]) for x in samples }
    dataloaders = { x: torch.utils.data.DataLoader(image_datasets[x], batch_size=batch_size, shuffle=shuffles[x], num_workers=num_workers) for x in samples }
    dataset_sizes = { x: len(image_datasets[x]) for x in samples }
    class_names = image_datasets['train'].classes
    
    return dataloaders, dataset_sizes, class_names, len(class_names)

def train_model(model, criterion, optimizer, scheduler, dataloaders, dataset_sizes, num_epochs, is_inception):
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    Result = namedtuple('Result', 'phase loss acc')

    since = time.time()

    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0
    
    for epoch in range(num_epochs):
        results = []
        # Each epoch has a training and validation phase
        for phase in ['train', 'test']:
            if phase == 'train':
                model.train()  # Set model to training mode
            else:
                model.eval()   # Set model to evaluate mode

            running_loss = 0.0
            running_corrects = 0

            # Iterate over data.
            for inputs, labels in dataloaders[phase]:
                inputs = inputs.to(device)
                labels = labels.to(device)

                # zero the parameter gradients
                optimizer.zero_grad()

                # forward
                # track history if only in train
                with torch.set_grad_enabled(phase == 'train'):
                    if is_inception and phase == 'train':
                        outputs, aux_outputs = model(inputs)
                        loss1 = criterion(outputs, labels)
                        loss2 = criterion(aux_outputs, labels)
                        loss = loss1 + 0.4*loss2
                    else:
                        outputs = model(inputs)
                        loss = criterion(outputs, labels)
                        
                    _, preds = torch.max(outputs, 1)
                    
                    # backward + optimize only if in training phase
                    if phase == 'train':
                        loss.backward()
                        optimizer.step()
                        scheduler.step()

                # statistics
                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = running_corrects.double() / dataset_sizes[phase]
            
            result = Result(phase, epoch_loss, float(str(epoch_acc.cpu().numpy())))
            results.append(result)

            # deep copy the model
            if phase == 'test' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model_wts = copy.deepcopy(model.state_dict())
        
        results = ['{} loss: {:.4f} acc: {:.4f}'.format(r.phase, r.loss, r.acc) for r in results]
        results = ' | '.join(results)
        print('Epoch {}/{} | {}'.format(epoch, num_epochs - 1, results))

    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(time_elapsed // 60, time_elapsed % 60))
    print('Best val Acc: {:4f}'.format(best_acc))

    # load best model weights
    model.load_state_dict(best_model_wts)
    return model

def get_metrics(model, dataloaders, class_names):
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    Metric = namedtuple('Metric', 'clazz tn fp fn tp sen spe acc f1 mcc')

    y_true = []
    y_pred = []
    was_training = model.training
    model.eval()

    with torch.no_grad():
        for i, (inputs, labels) in enumerate(dataloaders['valid']):
            inputs = inputs.to(device)
            labels = labels.to(device)
            cpu_labels = labels.cpu().numpy()

            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)

            for j in range(inputs.size()[0]):
                cpu_label = f'{cpu_labels[j]:02}'
                clazz_name = class_names[preds[j]]
                
                y_true.append(cpu_label)
                y_pred.append(clazz_name)
                
        model.train(mode=was_training)
    
    cmatrices = multilabel_confusion_matrix(y_true, y_pred, labels=class_names)
    metrics = []
    for clazz in range(len(cmatrices)):
        cmatrix = cmatrices[clazz]
        tn, fp, fn, tp = cmatrix[0][0], cmatrix[0][1], cmatrix[1][0], cmatrix[1][1]
        sen = tp / (tp + fn)
        spe = tn / (tn + fp)
        acc = (tp + tn) / (tp + fp + fn + tn)
        f1 = (2.0 * tp) / (2 * tp + fp + fn)
        mcc_denom = np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
        mcc = (tp * tn - fp * fn) / mcc_denom if mcc_denom > 0 else 0
        metric = Metric(clazz, tn, fp, fn, tp, sen, spe, acc, f1, mcc)
        metrics.append(metric)
    
    return metrics

def print_metrics(metrics):
    for m in metrics:
        print('{}: sen = {:.5f}, spe = {:.5f}, acc = {:.5f}, f1 = {:.5f}, mcc = {:.5f}'
              .format(m.clazz, m.sen, m.spe, m.acc, m.f1, m.mcc))

def parse_args(args):
    """
    Parses arguments.
    :return: Arguments.
    """
    parser = argparse.ArgumentParser('PyTorch classification models')
    parser.add_argument('-m', '--model', help='model', required=True)
    parser.add_argument('-d', '--data_dir', help='data directory', required=True)
    parser.add_argument('-b', '--batch_size', help='batch size', required=False, default=4, type=int)
    parser.add_argument('-e', '--epochs', help='number of epochs', required=False, default=25, type=int)
    parser.add_argument('--pretrained', help='use transfer learning', required=False, default=True, type=bool)
    parser.add_argument('--optimizer', help='optimizer options', required=False, default='{"lr": 0.001, "momentum": 0.9}', type=json.loads)
    parser.add_argument('--scheduler', help='scheduler options', required=False, default='{"step_size": 7, "gamma": 0.1}', type=json.loads)
    parser.add_argument('-w', '--num_workers', help='number of workers', required=False, default=4, type=int)
    parser.add_argument('-s', '--seed', help='seed', required=False, default=37, type=int)

    return parser.parse_args(args)


def do_it(args):
    data_dir = args.data_dir
    input_size = get_input_size(args.model)
    batch_size = args.batch_size
    num_workers = args.num_workers

    dataloaders, dataset_sizes, class_names, num_classes = get_dataloaders(data_dir, input_size, batch_size, num_workers)
    model = get_model(args.model, num_classes, args.pretrained)
    criterion = get_criterion()
    optimizer = get_optimizer(model, args.optimizer)
    scheduler = get_scheduler(optimizer, args.scheduler)

    num_epochs = args.epochs
    is_inception = determine_inception(args.model)
    model = train_model(model, criterion, optimizer, scheduler, dataloaders, dataset_sizes, num_epochs=num_epochs, is_inception=is_inception)

    print_metrics(get_metrics(model, dataloaders, class_names))

    print('done')


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    do_it(args)