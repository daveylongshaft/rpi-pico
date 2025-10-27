import math



def thermistorTemp(vout):
    vin = 3.3
    if vin-vout == 0:
        return -1
    ro = 1000
#    A = 0.001129148
#    B = 0.000234125
#    C = 0.0000000876741
    A = 0.006865031307231973
    B = -0.00088687906002218
    C = 5.870289299193854e-06
    R = ((vout*ro) / (vin-vout))
    if R > 0:
        mro = math.log(R)
    else:
        return -1
    mp = math.pow(mro,3)
    mroB = mro * B
    mpC = mp * C
    tempk = 1/(A+(mroB) + (mpC))
    tempc = tempk - 273.15
    #tempf = (tempc *9/5)+32
    return  tempc
    