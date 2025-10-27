#RPi pico W pinout
def pinout():
    print("""
                             ---usb---
                    GP0   1  |o     o| 40  VBUS
                    GP1   2  |o     o| 39  VSYS
                    GND   3  |o     o| 38  GND
                    GP2   4  |o     o| 37  3V3_EN
                    GP3   5  |o     o| 36  3V3(OUT)
                    GP4   6  |o     o| 35           ADC_VREF
                    GP5   7  |o     o| 34  GP28     ADC2
                    GND   8  |o     o| 33  GND      AGND
                    GP6   9  |o     o| 32  GP27     ADC1
                    GP7   10 |o     o| 31  GP26     ADC0
                    GP8   11 |o     o| 30  RUN
                    GP9   12 |o     o| 29  GP22
                    GND   13 |o     o| 28  GND
                    GP10  14 |o     o| 27  GP21
                    GP11  15 |o     o| 26  GP20
                    GP12  16 |o     o| 25  GP19
                    GP13  17 |o     o| 24  GP18
                    GND   18 |o     o| 23  GND
                    GP14  19 |o     o| 22  GP17
                    GP15  20 |o     o| 21  GP16
                             ---------
    """)
pinout()