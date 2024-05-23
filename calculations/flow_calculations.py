import logging
import logging.config
from os import path
import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)
logger.propagate = False

def overfall(level, skibordshojd, skibordsbredd, unit, dataframe=False):
    # Beräkning från https://pub.epsilon.slu.se/11781/11/persson_j_etal_150203.pdf
    logging.info("Utför överfallsberäkning")
    try:
        np.seterr(divide='ignore', invalid='ignore')
        g = 9.81  # m/s^2
        b = float(skibordsbredd)  # m
        p = float(skibordshojd)  # m
        h = np.array(level) - p  # nivå minus skibordshöjd, vattennivå över skibord
        h[h < 0] = 0  # inget flöde över, negativa höjder tas bort
        Ce = 0.602 + 0.083 * h / p  # har även sätt 0.075 * h / p användas

        # Går att lägga till ytterligare i app för att hantera detta vid behov
        if np.any(h/p > 1):
            logging.info("Nivå över skibordshöjd är \
            lika stor som skibordshöjd i någon punkt")
        if b < 0.3:
            logging.info("Vald skibordsbredd mindre än 30 cm, borde vara minst 30 cm för att beräkning ska fungera")
        if p < 0.3:
            logging.info("Vald skibordshöjd mindre än 30 cm, borde vara minst 30 cm för att beräkning ska fungera")
        if np.any(h) > 0.75:
            logging.info("Nivå över skibordshöjd över 75 cm, beräkning kanske inte stämmer.")
        # "h skall vara minst 3 cm och högst 75 cm" ska minst 3 cm verkligen tas med?
        #  if np.any(h) < 0.03:
        #    print("Varning: Nivå över skibordshöjd under 3 cm, beräkning kanske inte stämmer")

        # with np.errstate(divide='ignore', invalid='ignore'):
        Q = Ce * 2/3 * np.sqrt(2*g)*b*h**1.5
        Q[np.isnan(Q)] = 0.0  # Convert NaNs to 0.0

        if unit == "l/s":
            Q *= 1000 # 1 m3/s = 1000 l/s

        if dataframe:
            result_df = pd.DataFrame(Q, index=level.index, columns=[f'Flödes ({unit})'])
            return result_df
        logging.info("Överfallsberäkning utfördes")
        return Q.flatten()
    
    except Exception as Argument:
        logging.exception("Exception occured")
        raise ValueError(f"Error: {Argument}") from Argument


def cole_white_flow_calc(level, slope, diameter, roughness, unit, dataframe=True, velocity_output=False):
    logging.info("Utför rörberäkning")
    try:
        np.seterr(divide='ignore', invalid='ignore')
        # print("min level", min(level))

        # konstanter
        g = 9.81
        v = 1.0034

        # inputparameterar
        r = float(diameter) / 2 # enhet?
        k = float(roughness) # enhet?
        S = float(slope) # enhet?
        h = np.array(level)

        # definera shape output array
        Q = np.zeros(np.shape(h))

        # runt rör
        # for full pipe
        A = np.pi * r**2
        R = r / 2  # "hydraulic raduis of a full pipe is simply half of its radius"
        Q[h > 2 * r] = np.sqrt(32*g*R*S) * A * np.log10(
            k / (14.83 * R) + 2.52 * v / (R*np.sqrt(128*g*R*S))
        )

        # partially full
        θ = (2 * np.arccos((r - h[h <= 2 * r]) / r)) # arc length 
        A = r**2 * (θ - np.sin(θ)) / 2
        P = r * θ
        R = A / P
        Q[h <= 2 * r] = np.sqrt(32*g*4*R*S) * A * np.log10(k / (14.83 * 4*R) + 2.52 * v / (R*np.sqrt(128*g*R*S)))

        Q[np.isinf(Q)] = np.nan  # ifall det finns oänliga värden, konvertera dem till NaN

        if unit == "l/s":
            Q *= 1000  # 1 m3/s = 1000 l/s
            
        if velocity_output:
            if np.all(h) <= 2 * r:
                A = np.pi * r**2
            #print("Ashape", A)
            #print(Q*A.item())
            return (Q/A.item())#.flatten() #
        
        if dataframe:
            result_df = pd.DataFrame(Q, index=level.index, columns=[f'Flöde ({unit})'])
            return result_df
        
        
    
        logging.info("Rörberäkning utfördes")
        return Q.flatten()
    

    except Exception as Argument:
        logging.exception("Exception occured")
        raise ValueError(f"Error: {Argument}") from Argument



def cole_white_new(level, slope, diameter, roughness, unit, dataframe=True, velocity_output=False, index=None):
    logging.info("Utför rörberäkning")
    try:
        np.seterr(divide='ignore', invalid='ignore')

        # Constants
        g = 9.81 # m/s^2
        v = 1.0034e-6  # kinematic viscosity in m^2/s, corrected unit

        # Input parameters
        r = float(diameter) / 2 / 1000 # expected input is in mm converting to m, dividing by 2 for radius
        k = float(roughness) / 1000 # expected input is in mm converting to m
        S = float(slope) / 1000 # expected input is in per mil. 
        h = np.array(level) # expected input is in m

        # Define shape output array
        Q = np.zeros(np.shape(h))

        # Full pipe condition
        A_full = np.pi * r**2
        R_full = r / 2
        full_pipe = h > 2 * r

        θ = 2 * np.arccos((r - h[~full_pipe]) / r)
        A_partial = r**2 * (θ - np.sin(θ)) / 2 # positiv
        P_partial = r * θ
        R_partial = A_partial / P_partial

        if velocity_output:
            velocity = np.zeros_like(Q)
            velocity[full_pipe] = np.abs((
                np.sqrt(32 * g * R_full * S) * np.log10(
                    k / (14.83 * R_full) + 2.52 * v / (R_full * np.sqrt(128 * g * R_full * S))
                )))

            velocity[~full_pipe] = np.abs((
                np.sqrt(32 * g * R_partial * S) * np.log10(
                    k / (14.83 * R_partial) + 2.52 * v / (R_partial * np.sqrt(128 * g * R_partial * S))
                )))
            return velocity
        
        Q[full_pipe] = (
            np.abs(np.sqrt(32 * g * R_full * S) * A_full * np.log10(
                k / (14.83 * R_full) + 2.52 * v / (R_full * np.sqrt(128 * g * R_full * S))
            )))
        Q[~full_pipe] = (
            np.abs(np.sqrt(32 * g * R_partial * S) * A_partial * np.log10(
                k / (14.83 * R_partial) + 2.52 * v / (R_partial * np.sqrt(128 * g * R_partial * S))
            )))
        
        Q[np.isinf(Q)] = np.nan  # Convert infinite values to NaN

        if unit == "l/s":
            Q *= 1000  # Convert m^3/s to l/s

        if dataframe:
            if index is not None:
                result_df = pd.DataFrame(Q, index=index, columns=[f'Flöde ({unit})'])
            else:
                result_df = pd.DataFrame(Q, index=level.index, columns=[f'Flöde ({unit})'])
            return result_df

        logging.info("Rörberäkning utfördes")
        print("Rörberäkning utfördes")
        return Q.flatten()

    except Exception as Argument:
        print(f"exception {Argument}")
        logging.exception("Exception occured")
        raise ValueError(f"Error: {Argument}") from Argument

def cole_white_with_loss(level, slope, diameter, roughness, unit, dataframe=True):
    g = 9.82
     
    h = np.array(level)
    v = cole_white_new(level, slope, diameter, roughness, unit, velocity_output=True)
    #print(v)
    h_calc = 1.5 * v**2 / ( 2 * g)
    #print("h calc", h_calc)
    
    h = h - h_calc
    #print(h)
    
    Q = cole_white_new(level, slope, diameter, roughness, unit, index=level.index, dataframe=dataframe)
    #print(Q)
    return Q


def iteration_test(level, slope, diameter, roughness, unit):
    g = 9.82
    
    h_org = np.array(level)
    h = h_org
    i = 0
    while True:
        v = cole_white_new(h, slope, diameter, roughness, unit, velocity_output=True)
        print("v", v)
        h_loss = 1.5 * v**2 / (2 * g)
        if np.abs(np.sum(h) - np.sum(h_org - h_loss)) < 0.005:
            return h
            #break
        h = h_org - h_loss
        print("h", h)
        
        if i > 150:
            print("did not converge")
            return None
        i += 1
        
    #print(v)
   
    print("h calc", h_calc)
    i = 0
    
    h = h - h_calc
    print(h)
    
    #Q = cole_white_new(h, 3, 330, 1, "m3/s", index=level.index)
    #print(Q)
    h_org 
    while np.any(np.abs(h - h_calc)) > 0.03:
        h = h - h_calc
        print("h original", h)
        #h = h_calc
        v = cole_white_new(h, slope, diameter, roughness, unit, velocity_output=True)
        h_calc = 1.5 * v**2 / ( 2 * g)
        print("h calc", h_calc)
        print("v:", v)
        #print("h_calc", h_calc)
        #print(np.abs(h-h_calc))
        i += 1
        if i > 4:
            break
            
#h= 0.1 * np.random.rand(1, size=(100)) #0.1 m           
#iteration_test(h, 3, 330, 1, "m3/s")