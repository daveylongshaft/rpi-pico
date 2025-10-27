import math

def thermistorTempOld(Vout):

    # Voltage Divider
    Vin = 3.3
    Ro = 10000  # 10k Resistor

    # Steinhart Constants
    A = 0.001129148
    B = 0.000234125
    C = 0.0000000876741

    # Calculate Resistance
    Rt = ((Vout * Ro) / (Vin - Vout)) 
    
    # Steinhart - Hart Equation
    TempK = 1 / (A + (B * math.log(Rt)) + C * math.pow(math.log(Rt), 3))

    # Convert from Kelvin to Celsius
    #TempC =  273.15 - TempK
    TempC = 367 - TempK
    TempF = (TempC *9/5)+32
    return  TempF

def thermistorTemp(vout):
    vin = 3.3
    if vin-vout == 0:
        return -1
    ro = 1000
    A = 0.001129148
    B = 0.000234125
    C = 0.0000000876741
    R = ((vout*ro) / (vin-vout))
    if R > 0:
        mro = math.log(R)
    else:
        return -1
    mp = math.pow(mro,3)
    mroB = mro * B
    mpC = mp * C
    tempk = 1/(A+(mroB) + (mpC))
    tempc = 330 - tempk
    tempf = (tempc *9/5)+32
    return  tempf
    