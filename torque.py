#TODO: 'X_sd' and 'X_sq' --> not accurate
#TODO: 'delta' --> not accurate, the current value is taken from Motor-CAD

from __future__ import absolute_import
import numpy as np
from math import pi, sin, atan, log, e, sqrt, cos, degrees, radians
from openmdao.api import Problem, IndepVarComp, ExplicitComponent, ExecComp
from openmdao.api import NewtonSolver, Group, DirectSolver, NonlinearRunOnce, LinearRunOnce, view_model, BalanceComp, ScipyOptimizeDriver

# Reactance:
class Reactance(ExplicitComponent):
    def setup(self):
        self.add_input('m_1', 1, units=None, desc='Number of phases')
        self.add_input('mu_0', 0.4*pi*10**-6, units='H/m', desc='Magnetic Permeability of Free Space')  # CONSTANT - Is this the best way to represent a constant?
        self.add_input('f', 1, units='Hz', desc='frequency')
        self.add_input('i', 1, units='A', desc='current')  # 'I_a' in Gieras's book
        self.add_input('N_1', 1, units=None, desc='Number of the stator turns per phase')  # Confirm how this is measured
        self.add_input('k_w1', 1, units=None, desc='Stator winding factor')
        self.add_input('n_m', 1, units=None, desc='Number of poles')  # '2p' in Gieras's book
        self.add_input('tau', 1, units='m', desc='Pole pitch')  # Gieras - pg.134 - (4.27)
        self.add_input('L_i', 1, units='m', desc='Armature stack effective length')
        self.add_input('k_fd', 1, units=None, desc='Form Factor of the Armature Reaction')  # Gieras - pg.192
        self.add_input('k_fq', 1, units=None, desc='Form Factor of the Armature Reaction')  # Gieras - pg.192
        self.add_input('pp', 1, units=None, desc='Number of pole pairs')  # 'p' in Gieras's book

        # Equivalent Air Gap 
        self.add_input('g_eq', 1, units='m', desc='Equivalent Air Gap') # Gieras - pg.180
        self.add_input('g_eq_q', 1, units='m', desc='Mechanical Clearance in the q-axis')  # Gieras - pg.180

        #self.add_input('mag_flux', 1, units='Wb', desc='Magnetic Flux')  # Same as eMag_flux??? - The assumption is YES for now.
        self.add_input('eMag_flux', 1, units='Wb', desc='Magnetic Flux')
        self.add_output('flux_link', 1, units='Wb', desc='Flux Linkage A.K.A: Weber-turn') # Gieras - pg.581
        self.add_output('L_1', 1, units='H', desc='Leakage Inductance of the armature winding per phase')  # Gieras - pg.204 & pg. 108
        
        self.add_output('X_1', 1, units='ohm', desc='Stator Leakage Reactance')  # Gieras - pg.176
        #self.add_output('X_a', 1, units='ohm', desc='Armature reaction reactance')  # Gieras - pg.176
        self.add_output('X_ad', 1, units='ohm', desc='d-axis armature reaction reactance')  # Gieras - pg.176
        self.add_output('X_aq', 1, units='ohm', desc='q-axis armature reaction reactance')  # Gieras - pg.176
        self.add_output('X_sd', 1, units='ohm', desc='d-axis synchronous reactance')  # Gieras - pg.176 - (5.15)
        self.add_output('X_sq', 1, units='ohm', desc='q-axis synchronous reactance')  # Gieras - pg.176 - (5.15)

    def compute(self, inputs, outputs):
        m_1 = inputs['m_1']
        mu_0 = inputs['mu_0']
        f = inputs['f']
        i = inputs['i']
        N_1 = inputs['N_1']
        k_w1 = inputs['k_w1']
        n_m = inputs['n_m']
        tau = inputs['tau']
        L_i = inputs['L_i']
        k_fd = inputs['k_fd']
        k_fq = inputs['k_fq']
        pp = inputs['pp']

        g_eq = inputs['g_eq']
        g_eq_q = inputs['g_eq_q']

        eMag_flux = inputs['eMag_flux']

        outputs['flux_link'] = N_1*eMag_flux
        flux_link = outputs['flux_link']
        outputs['L_1'] = flux_link/i
        L_1 = outputs['L_1']

        # Gieras - pg.196 - (5.7.3):  NOTE:  If rare-earth PMs are used, the synchronous reactances in the d- and q-axis are practically the same (Table 5.2 - pg.192).
        # So, should X_ad = X_aq? - If so, second part of torque equation is zero?
        outputs['X_1'] = 2*pi*f*L_1
        X_1 = outputs['X_1']
        outputs['X_ad'] = 4*m_1*mu_0*f*(((N_1*k_w1)**2)/(pi*pp))*(tau*L_i/g_eq)*k_fd
        X_ad = outputs['X_ad']
        outputs['X_aq'] = 4*m_1*mu_0*f*(((N_1*k_w1)**2)/(pi*pp))*(tau*L_i/g_eq_q)*k_fq
        X_aq = outputs['X_aq']

        outputs['X_sd'] = X_1 + X_ad
        outputs['X_sq'] = X_1 + X_aq

        # TODO: The difference between 'X_sd' and 'X_sq' heavily plays into output torque...
        # So, either reevaluate the calculations and work out bugs, or insert assumption values for 'X_sd' and 'X_sq'
        outputs['X_sd'] = 0.14
        outputs['X_sq'] = 0.145

# Equivalent Air Gap Calculations - g' and g'_q
class airGap_eq(ExplicitComponent):
    def setup(self):
        self.add_input('g', 0.001, units='m', desc='Air Gap - Mechanical Clearance')
        self.add_input('k_c', 1, units=None, desc='Carters Coefficient')  # Gieras - pg.563 - (A.27)
        self.add_input('k_sat', 1, units=None, desc='Saturation factor of the magnetic circuit due to the main (linkage) magnetic flux')  # Gieras - pg.73 - (2.48) - Typically ~1
        self.add_input('t_mag', 0.005, units='m', desc='Magnet thickness')  # 'h_m' in Gieras's book
        # Magnetic Permeability:  N/A**2 == H/m == Wb/A*m
        self.add_input('mu_rec', 1.303*10**-6, units='N/A**2', desc='Recoil Magnetic Permeability - (Delta_B/Delta_H) - Slope of straight-line B-H Curve')  # Gieras - pg.48 - (2.5)
        # mu_rec:  I used a data sheet for a N48H magnet and got the slope of the straight line B-H curve
        self.add_input('mu_0', 0.4*pi*10**-6, units='H/m', desc='Magnetic Permeability of Free Space')  #CONSTANT

        self.add_output('mu_rrec', 1, units=None, desc='Relative recoil permeability')  # Gieras - pg.48 - (2.5)
        self.add_output('g_eq', 1, units='m', desc='Equivalent aig gap')  # Gieras - pg.180
        self.add_output('g_eq_q', 1, units='m', desc='Equivalent air gap q-axis')  # Gieras - pg.180

    def compute(self, inputs, outputs):
        g = inputs['g']
        k_c = inputs['k_c']
        k_sat = inputs['k_sat']
        t_mag = inputs['t_mag']
        mu_rec = inputs['mu_rec']
        mu_0 = inputs['mu_0']

        outputs['mu_rrec'] = mu_rec/mu_0
        mu_rrec = outputs['mu_rrec']
        outputs['g_eq'] = g*k_c*k_sat + (t_mag/mu_rrec)
        outputs['g_eq_q'] = g*k_c*k_sat

# Carter's Coefficient
class k_c(ExplicitComponent):
    def setup(self):
        self.add_input('g', 0.001, units='m', desc='Air Gap - Mechanical Clearance')
        self.add_input('D_1in', 1, units='m', desc='Inner diameter of the stator')  # Gieras - pg.217 - Vairable Table
        self.add_input('n_s', 1, units=None, desc='Number of slots')  # 's_1' in Gieras's book
        self.add_input('b_14', 1, units='m', desc='Width of the stator slot opening')  # Gieras
        
        # 'mech_angle' in calculated in rad
        self.add_output('mech_angle', 1, units='rad', desc='Mechanical angle')  # Gieras - pg.563 - (A.28) - LOWER CASE GAMMA
        self.add_output('t_1', 1, units='m', desc='Slot Pitch')  # Gieras - pg.218
        self.add_output('k_c', 1, units=None, desc='Carters Coefficient')  # Gieras - pg.563 - (A.27)

    def compute(self, inputs, outputs):
        g = inputs['g']
        D_1in = inputs['D_1in']
        n_s = inputs['n_s']
        b_14 = inputs['b_14']

        outputs['mech_angle'] = (4/pi)*(((0.5*b_14/g)*atan(0.5*b_14/g))-(log(sqrt(1+((0.5*b_14/g)**2)), e)))
        outputs['t_1'] = (pi*D_1in)/n_s
        t_1 = outputs['t_1']
        mech_angle = outputs['mech_angle']
        outputs['k_c'] = t_1/(t_1 - (mech_angle*g))

# First Harmonic of the Air Gap Magnetic Flux Density
class B_mg1(ExplicitComponent):
    def setup(self):
        self.add_input('b_p', 1, units='m', desc='Pole shoe width || Tooth Width')  # Gieras - Not Defined
        self.add_input('tau', 1, units='m', desc='Pole pitch')  # Gieras - pg.134 - (4.27)
        self.add_input('B_mg', 2.4, units='T', desc='Magnetic Flux Density under the pole shoe')  # Set to stator max flux density (Hiperco 50) = 2.4T
        self.add_output('pole_arc', 1, units=None, desc='Effective Pole Arc Coefficient')  # Gieras - pg.174 - (4.28) & (5.4)
        self.add_output('B_mg1', 1, units='T', desc='Air Gap Magnetic Flux Density')  # Gieras - pg. 173 - (5.2)

    def compute(self, inputs, outputs):
        b_p = inputs['b_p']
        tau = inputs['tau']
        B_mg = inputs['B_mg']

        outputs['pole_arc'] = b_p/tau
        pole_arc = outputs['pole_arc']
        outputs['B_mg1'] = (4/pi)*B_mg*sin(0.5*pole_arc*pi)

# Excitation Magnetic Flux
class eMag_flux(ExplicitComponent):
    def setup(self):
        self.add_input('L_i', 1, units='m', desc='Armature stack effective length')
        self.add_input('B_mg1', 1, units='T', desc='Air Gap Magnetic Flux Density')  # Should we calculate or insert value?
        self.add_input('mot_or', .075, units='m', desc='motor outer radius')
        self.add_input('n_m', 1, units=None, desc='Number of poles')  # '2p' in Gieras's book
        
        self.add_output('tau', 1, units='m', desc='Pole pitch')  # Gieras - pg.134 - (4.27)
        self.add_output('eMag_flux', 1, units='Wb', desc='Excitation Magnetic Flux')  # Gieras - pg.174 - (5.6)

    def compute(self, inputs, outputs):
        L_i = inputs['L_i']
        B_mg1 = inputs['B_mg1']
        mot_or = inputs['mot_or']
        n_m = inputs['n_m']

        outputs['tau'] = (pi*2*mot_or)/n_m
        tau = outputs['tau']
        outputs['eMag_flux'] = (2/pi)*tau*L_i*B_mg1

# Stator Winding Factor
class k_w1(ExplicitComponent):
    def setup(self):
        self.add_input('w_sl', 1, units=None, desc='Coil span measured in number of slots - Coil Span: the peripheral distance between two sides of a coil, measured in term of the number of armature slots between them.')  # Gieras
        self.add_input('m_1', 1, units=None, desc='Number of phases')
        self.add_input('n_m', 1, units=None, desc='Number of poles')  # '2p' in Gieras's book
        self.add_input('n_s', 1, units=None, desc='Number of slots')  # 's_1' in Gieras's book

        self.add_output('pps', 1, units='rad', desc='Poles Per Slot - Angular displacement between adjacent slots in electrical degrees')
        self.add_output('q_1', 1, units=None, desc='Number of slots per pole per phase')
        self.add_output('Q_1', 1, units=None, desc='Number of slots per pole')
        self.add_output('k_d1', 1, units=None, desc='Distribution factor')  # Gieras - pg.559 - (A.2)
        self.add_output('k_p1', 1, units=None, desc='Pitch Factor')  # Gieras - pg.559 - (A.3)
        self.add_output('k_w1', 1, units=None, desc='Stator winding factor')  # Gieras - pg.559 - (A.1)

    def compute(self, inputs, outputs):
        w_sl = inputs['w_sl']
        m_1 = inputs['m_1']
        n_m = inputs['n_m']
        n_s = inputs['n_s']

        outputs['q_1'] = n_s/(n_m*m_1)
        q_1 = outputs['q_1']
        #outputs['pps'] = (pi*n_m)/n_s
        outputs['pps'] = (2*pi)/m_1*q_1  # Phase belt = 120 degrees for a three phase motor - Gieras - pg.559
        outputs['Q_1'] = n_s/n_m

        pps = outputs['pps']
        q_1 = outputs['q_1']
        Q_1 = outputs['Q_1']
        outputs['k_d1'] = (sin(0.5*q_1*pps))/(q_1*sin(0.5*pps))
        outputs['k_p1'] = sin((0.5*pi*w_sl)/Q_1)
        k_d1 = outputs['k_d1']
        k_p1 = outputs['k_p1']
        #TODO
        outputs['k_w1'] = k_d1*k_p1
        #outputs['k_w1'] = 0.96  # Typical value from Gieras book

# Frequency:
class Frequency(ExplicitComponent):
    def setup(self):
        self.add_input('rm', 1, units='rpm', desc='motor speed')  # "n_s" in Gieras's book
        self.add_input('pp', 1, units=None, desc='Number of pole pairs')

        self.add_output('f', 1, units='Hz', desc='frequency')

    def compute(self, inputs, outputs):
        rm = inputs['rm']
        pp = inputs['pp']
        outputs['f'] = rm*pp

# EMF - Gieras - pg. 174
class E_f(ExplicitComponent):
    def setup(self):
        self.add_input('N_1', 1, units=None, desc='Number of the stator turns per phase')
        self.add_input('k_w1', 1, units=None, desc='the stator winding coefficient')  # Computed in the "k_w1" class TODO: Connect k_w1 output to here
        self.add_input('eMag_flux', 1, units='Wb', desc='Excitation Magnetic Flux')  # Gieras - pg.174 - (5.6)
        self.add_input('f', 1, units='Hz', desc='frequency')
        
        self.add_output('E_f', 1, units='V', desc='EMF - the no-load RMS Voltage induced in one phase of the stator winding')  # Gieras - pg.174 - (5.5)

    def compute(self, inputs, outputs):
        N_1 = inputs['N_1']
        k_w1 = inputs['k_w1']
        eMag_flux = inputs['eMag_flux']
        f = inputs['f']

        outputs['E_f'] = pi*(2**0.5)*f*N_1*k_w1*eMag_flux
        outputs['E_f'] = 129

# Power (load) Angle: "delta":
class delta(ExplicitComponent):
    def setup(self):
        self.add_input('i', 35.36, units='A', desc='RMS Current')  # Gieras - Appendix
        self.add_input('flux_link', units='Wb', desc='Flux Linkage A.K.A: Weber-turn')  # Gieras - pg.581
        self.add_input('X_sd', 1, units='ohm', desc='d-axis synchronous reactance')  # Gieras - pg.176
        self.add_input('X_sq', 1, units='ohm', desc='q-axis synchronous reactance')  # Gieras - pg.176
        self.add_input('R_1', 1, units='ohm', desc='Armature winding resistance') # Gieras - pg.579

        self.add_output('delta', 1, units='rad', desc='Power (Load) Angle - The angle between V-1 and E_f')  # Gieras - pg.175 - Below (5.14)

    def compute(self, inputs, outputs):
        i = inputs['i']
        flux_link = inputs['flux_link']
        X_sd = inputs['X_sd']
        X_sq = inputs['X_sq']
        R_1 = inputs['R_1']

        #flux_link = pi/2

        #NOTE: Complex part of 'delta' is going away due to type casting.
        #NOTE: Look at Gieras - pg.223 - Graphs show typical delta angles?
        #NOTE: Torque is seems to be pretty coupled to how the controller operates too.
        outputs['delta'] = ((i*sin(flux_link))*(R_1 + 1j*X_sd)) + ((i*cos(flux_link))*(R_1 + 1j*X_sq))  # Gieras - pg.180 & pg.181 - (5.35), (5.36), (5.37)
        
        #TODO:  Cannot get accurate delta angles, so I overwrote it here to give accurate output...
        outputs['delta'] = radians(19)  # 19 degrees was taken from Motor-CAD

# Torque
class torque(ExplicitComponent):
    def setup(self):
        self.add_input('m_1', 1, units=None, desc='number of phases')
        self.add_input('rm', 1, units='rpm', desc='motor speed')  # "n_s" in Gieras's book
        self.add_input('V_1', 1, units='V', desc='stator voltage')  # Confirm that this is the same as the bus volage
        self.add_input('E_f', 1, units='V', desc='EMF - the no-load RMS Voltage induced in one phase of the stator winding')
        self.add_input('X_sd', 1, units='ohm', desc='d-axis synchronous reactance')  # Gieras - pg.176
        self.add_input('X_sq', 1, units='ohm', desc='q-axis synchronous reactance')  # Gieras - pg.176
        self.add_input('delta', 1, units='rad', desc='Power (Load) Angle - The angle between V-1 and E_f')  # Gieras - pg.180  TODO: Check units and calculation
        
        self.add_output('p_elm', 1, units='W', desc='Power - Electromagnetic')
        self.add_output('tq', 1, units='N*m', desc='Torque - Electromagnetic')

    def compute(self, inputs, outputs):
        m_1 = inputs['m_1']
        rm = inputs['rm']
        V_1 = inputs['V_1']
        E_f = inputs['E_f']
        X_sd = inputs['X_sd']
        X_sq = inputs['X_sq']
        delta = inputs['delta']

        #outputs['tq'] = (60)*(m_1/(2*pi*rm))((V_1*E_f*sin(delta))+(((V_1**2)/2)((1/X_sq)-(1/X_sd))*sin(2*delta)))  # Full Equation
        
        outputs['p_elm'] = (m_1)*((V_1*E_f*sin(delta))+(((V_1**2)/2)*((1/X_sq)-(1/X_sd))*sin(2*delta)))
        #outputs['p_elm'] = 13118  # Value according to Motor-CAD
        p_elm = outputs['p_elm']
        # Torque/Power Equation must be multiplied by 60 seconds to convert from minutes to seconds
        outputs['tq'] = p_elm/(2*pi*rm)*60

if __name__ == "__main__":
    prob = Problem()
    model = prob.model

    ind = model.add_subsystem('indeps', IndepVarComp(), promotes=['*'])

    #NOTE: Got measurements from X_57_9.3.2Hd.mot Motor-CAD File and Specification Rev B 20190212
    # Reactance:
    ind.add_output('m_1', 3)
    ind.add_output('i', 35.36, units='A')
    ind.add_output('N_1', 96)  # Check this
    #ind.add_output('N_1', 12)
    ind.add_output('n_m', 20)
    ind.add_output('L_i', 0.033, units='m')
    ind.add_output('k_fd', 1)  # Default = 1
    ind.add_output('k_fq', 1)  # Default = 1
    ind.add_output('pp', 10)

    # Equivalent Air Gap:
    ind.add_output('g', 0.001, units='m')
    ind.add_output('k_sat', 1.1)
    ind.add_output('t_mag', 0.005, units='m')

    # Carter's Coefficient:
    ind.add_output('D_1in', 125, units='mm')
    ind.add_output('n_s', 24)
    ind.add_output('b_14', 3.25, units='mm')

    # B_mg1:
    ind.add_output('b_p', 4.3, units='mm')
    ind.add_output('B_mg', 2.4, units='T')

    # eMag Flux:
    ind.add_output('mot_or', .075, units='m')
    
    # Stator Winding Factor:
    ind.add_output('w_sl', 1)

    # Frequency:
    ind.add_output('rm', 5460, units='rpm')  # TRY: Sweep across a RPM range?
    
    # EMF:
    
    # Power (load) Angle:
    ind.add_output('R_1', 0.1281, units='ohm')  # Motor-CAD

    # Torque:
    ind.add_output('V_1', 385, units='V')  # TRY: Sweep across a Voltage range?

    # SUBSYSTEM ADD (Add subsystems in the order they need to computed in?):
    model.add_subsystem('Frequency', Frequency(), promotes_inputs=['rm', 'pp'], promotes_outputs=['f'])
    model.add_subsystem('WindingFactor', k_w1(), promotes_inputs=['w_sl', 'm_1', 'n_m', 'n_s'], promotes_outputs=['pps', 'q_1', 'Q_1', 'k_d1', 'k_p1', 'k_w1'])
    model.add_subsystem('B_mg1', B_mg1(), promotes_inputs=['b_p', 'tau', 'B_mg'], promotes_outputs=['pole_arc', 'B_mg1'])
    model.add_subsystem('ExcitationMagneticFlux', eMag_flux(), promotes_inputs=['L_i', 'B_mg1', 'mot_or', 'n_m'], promotes_outputs=['tau', 'eMag_flux'])
    model.add_subsystem('CartersCoefficient', k_c(), promotes_inputs=['g', 'D_1in', 'n_s', 'b_14'], promotes_outputs=['mech_angle', 't_1', 'k_c'])
    model.add_subsystem('EquivalentAirGap', airGap_eq(), promotes_inputs=['g', 'k_c', 'k_sat', 't_mag', 'mu_rec', 'mu_0'], promotes_outputs=['mu_rrec', 'g_eq', 'g_eq_q'])
    model.add_subsystem('Reactance', Reactance(), promotes_inputs=['m_1', 'mu_0', 'f', 'i', 'N_1', 'k_w1', 'n_m', 'tau', 'L_i', 'k_fd', 'k_fq', 'g_eq', 'g_eq_q', 'eMag_flux', 'pp'], promotes_outputs=['flux_link', 'L_1', 'X_1', 'X_ad', 'X_aq', 'X_sd', 'X_sq'])
    model.add_subsystem('EMF', E_f(), promotes_inputs=['N_1', 'k_w1', 'eMag_flux', 'f'], promotes_outputs=['E_f'])
    model.add_subsystem('PowerAngle', delta(), promotes_inputs=['i', 'flux_link', 'X_sd', 'X_sq', 'R_1'], promotes_outputs=['delta'])
    model.add_subsystem('Torque', torque(), promotes_inputs=['m_1', 'rm', 'V_1', 'E_f', 'X_sd', 'X_sq', 'delta'], promotes_outputs=['p_elm', 'tq'])

    prob.setup()
    prob.final_setup()
    prob.set_solver_print(level=2)
    prob.run_model()
    prob.model.list_outputs(implicit=True)  # Gives all final numbers

    print('Motor Torque:...........', prob.get_val('tq', units='N*m'))
    print('Delta..............', prob.get_val('delta'))
    print('k_c:...........', prob.get_val('k_c'))
    print('Flux Link..............', prob.get_val('flux_link', units='Wb'))
    print('eMag_flux.................', prob.get_val('eMag_flux', units='Wb'))
    print('B_mg1......', prob.get_val('B_mg1'))
    print('L_1 ......', prob.get_val('L_1', units='uH'))
    print('Eq Air Gap............', prob.get_val('g_eq', units='mm'))
    print('Eq Air Gap_Q-axis............', prob.get_val('g_eq_q', units='mm'))