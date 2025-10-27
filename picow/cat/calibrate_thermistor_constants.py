import numpy as np
from scipy.optimize import fsolve

# Measured temperatures (Kelvin) and resistances (Ohms)

T1, T2, T3 = 273.15, 298.15, 373.15
R1, R2, R3 = 17200, 11200, 900

# Function representing the system of equations
def steinhart_hart(params):
    A, B, C = params
    eq1 = 1/T1 - (A + B*np.log(R1) + C*(np.log(R1))**3)
    eq2 = 1/T2 - (A + B*np.log(R2) + C*(np.log(R2))**3)
    eq3 = 1/T3 - (A + B*np.log(R3) + C*(np.log(R3))**3)
    return [eq1, eq2, eq3]

# Initial guess for A, B, C
initial_guess = [0.001, 0.001, 0.001]

# Solve for A, B, C
A, B, C = fsolve(steinhart_hart, initial_guess)

print(f"Calibrated Steinhart-Hart constants:\nA = {A}\nB = {B}\nC = {C}")