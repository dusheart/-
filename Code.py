import time

import torch
import xlrd
from torch import nn, double
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
import pandas
import matplotlib.pyplot as plt
from torch.nn import functional as F

#超参数
#全连接网络的输入与输出
Finput_size=42
Fhidden_size=20
Foutput_size=10
#RNN的输入与隐藏层和层数
input_size=3
hidden_size=10
num_layers=1
#RNN前驱体的输入
h0_input_size=8
h0_hidden_size=10
#数据获取的根目录
root='datas.xlsx'
#训练集占比和验证集占比
train_ratio=0.7
valratio=0.1
#训练过程的相关参数
max_epoch=100
batch=5
device='cuda'
#model建立
class ANNmodel(nn.Module):
    def __init__(self):
        super(ANNmodel, self).__init__()
        self.net=nn.Sequential(
            nn.Linear(Finput_size,Fhidden_size),
            nn.ReLU(),
            nn.Linear(Fhidden_size,Fhidden_size),
            nn.ReLU(),
            nn.Linear(Fhidden_size,Foutput_size),
        )
    def forward(self,x):
        output=self.net(x)
        return output

class RNNmodel(nn.Module):
    def __init__(self):
        super(RNNmodel, self).__init__()
        self.net=nn.Sequential(
            nn.Linear(h0_input_size,h0_hidden_size),
            nn.ReLU(),
            nn.Linear(h0_hidden_size,hidden_size),
        )
        self.rnn=nn.RNN(input_size=input_size,hidden_size=hidden_size,num_layers=num_layers,batch_first=True)

    def forward(self,x,h):
        h0=self.net(h)
        h0=h0.unsqueeze(0)
        output,hidden=self.rnn(x,h0)
        return output,hidden

#数据的类型的获得
class MyDataset(Dataset):
    def __init__(self,root,Train=True,Trainset_ratio=0.7,VAl=False,Valset_ratio=0.1):
        super(MyDataset, self).__init__()
        self.Train=Train
        self.Trainset_ratio=Trainset_ratio
        self.VAl=VAl
        self.Valset_ratio=Valset_ratio
        data= pandas.read_excel(root)
        data=data.values
        data=data[1:,2:]
        #归一化
        data=torch.tensor(data.astype(float))
        #data=F.normalize(data,p=1,dim=0)

        if(Train):
            data=data[:round(data.shape[0]*Trainset_ratio)]
            if (VAl):
                #验证集
                data=data[:round(data.shape[0]*Valset_ratio)]

                self.dataset=data
            else:

                #训练集
                data=data[round(data.shape[0]*Valset_ratio):]

                self.dataset=data

        else:
            #测试集
            data=data[round(data.shape[0]*Trainset_ratio):]
            self.dataset=data

    def __getitem__(self, index):
        if(self.Train):
            target=self.dataset[:,-10:]
            dataseries=self.dataset[:,8:-10]
            h0=self.dataset[:,:8]
            #dataseries=dataseries.reshape(dataseries.shape[0],-1,3)
            return h0[index],dataseries[index],target[index]
        else:
            h0=self.dataset[:,:8]
            dataseries=self.dataset[:,8:-10]
            #dataseries=dataseries.reshape(dataseries.shape[0],-1,3)
            return h0[index],dataseries[index]

    def __len__(self):
        return len(self.dataset)

#训练的主体流程
#数据集和数据加载器
Trianset=MyDataset(root=root,Train=True,Trainset_ratio=train_ratio)
Valset=MyDataset(root=root,Train=True,Trainset_ratio=train_ratio,VAl=True,Valset_ratio=valratio)
Testset=MyDataset(root=root,Train=False,Trainset_ratio=train_ratio)
Traindatalorder=torch.utils.data.DataLoader(Trianset,batch_size=batch,shuffle=True)
Valdatalorder=torch.utils.data.DataLoader(Valset,batch_size=batch,shuffle=True)
Testdatalorder=torch.utils.data.DataLoader(Testset)

MyANN=ANNmodel()
MyANN.to(device)
MyRNN=RNNmodel()
MyRNN.to(device)
#学习率，损失函数和优化器
lr=0.01
RNNoptimizer=torch.optim.Adagrad(params=MyRNN.parameters(),lr=lr)
ANNoptimizer=torch.optim.Adagrad(params=MyANN.parameters(),lr=lr)
criterion=torch.nn.MSELoss()
ANNcriterion=torch.nn.MSELoss()
MSEMAX=100000000
MSEANN=100000000

ANN_Train_loss=list(range(max_epoch))
RNN_Train_loss=list(range(max_epoch))
ANN_Test_loss=list(range(max_epoch))
RNN_Test_loss=list(range(max_epoch))
for epoch in range(max_epoch):
    for h,data_series,target in Traindatalorder:
        #ANN的训练过程
        #数据导入GPU
        ANN_input=data_series
        ANN_input=ANN_input.to(device)
        ANN_input=ANN_input.float()
        ANN_target=target
        ANN_target=ANN_target.to(device)
        ANN_target=ANN_target.float()
        ANNoptimizer.zero_grad()
        ANN_output=MyANN(ANN_input)
        ANN_output.to(device)
        ANN_loss=ANNcriterion(ANN_output,ANN_target)
        ANNoptimizer.zero_grad()
        ANN_loss.backward()
        ANNoptimizer.step()



        #RNN的训练过程
        #数据导入GPU
        RNN_h0=h
        RNN_h0=RNN_h0.to(device)
        RNN_h0=RNN_h0.float()
        RNN_input=data_series.reshape(data_series.shape[0],-1,3)
        RNN_input=RNN_input.to(device)
        RNN_input=RNN_input.float()
        hidden=target.to(device)
        hidden=hidden.float()
        RNNoptimizer.zero_grad()
        output,hiddenoutput=MyRNN(RNN_input,RNN_h0)
        hiddenoutput=torch.squeeze(hiddenoutput,dim=0)
        loss=criterion(hidden,hiddenoutput)
        RNNoptimizer.zero_grad()
        loss.backward()
        RNNoptimizer.step()

    ANN_Train_loss[epoch]=ANN_loss.item()
    if(MSEANN-ANN_loss.item()>0):
        MSEANN=ANN_loss.item()
        print("epoch:{epoch},ANNTrainloss:{loss}".format(epoch=epoch,loss=MSEANN))
        prefix = 'checkpoints/'
        name = time.strftime(prefix + 'ANN%m%d-%H-%M-%S.pth')


    RNN_Train_loss[epoch]=loss.item()
    if(MSEMAX-loss.item()>0):
        MSEMAX=loss.item()
        print("epoch:{epoch},RNNTrainloss:{loss}".format(epoch=epoch,loss=MSEMAX))
        prefix = 'checkpoints/'
        name = time.strftime(prefix + 'RNN%m%d-%H-%M-%S.pth')




#验证模型的性能

    total_loss=0
    ANN_Total_loss=0
    with torch.no_grad():
        for h,data_series,target in Valdatalorder:




            RNN_h0=h
            RNN_h0=RNN_h0.to(device)
            RNN_h0=RNN_h0.float()
            RNN_input=data_series.reshape(data_series.shape[0],-1,3)
            RNN_input=RNN_input.to(device)
            RNN_input=RNN_input.float()
            hidden=target.to(device)
            hidden=hidden.float()


            ANN_input=data_series
            ANN_input=ANN_input.to(device)
            ANN_input=ANN_input.float()


            ANN_output=MyANN(ANN_input)
            ANN_loss=ANNcriterion(ANN_output,hidden)
            ANN_Total_loss=ANN_Total_loss+ANN_loss.item()


            output,hiddenoutput=MyRNN(RNN_input,RNN_h0)
            hiddenoutput=torch.squeeze(hiddenoutput,dim=0)
            loss=criterion(hidden,hiddenoutput)
            total_loss=total_loss+loss.item()

        ANN_Test_loss[epoch]=ANN_Total_loss
        RNN_Test_loss[epoch]=total_loss
        #print("epoch:{epoch},RNNValidationloss:{loss}".format(epoch=epoch,loss=total_loss))
        #print("epoch:{epoch},ANNValidationloss:{loss}".format(epoch=epoch,loss=ANN_Total_loss))

#绘制损失函数图像
plt.figure()
plt.plot(ANN_Train_loss,'b',label = 'ANN_Train_loss')
plt.plot(RNN_Train_loss,'g',label = 'RNN_Train_loss')
plt.plot(ANN_Test_loss,'r',label = 'ANN_Test_loss')
plt.plot(RNN_Test_loss,'y',label = 'RNN_Test_loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend()
plt.show()















