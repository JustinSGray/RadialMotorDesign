import numpy as np
from math import pi

import openmdao.api as om

class MotorSizeComp(om.ExplicitComponent):

    def setup(self):
        self.add_input('radius_motor', 0.078225, units='m', desc='outer radius of motor')
        self.add_input('gap', 0.001, units='m', desc='air gap')
        self.add_input('rot_or', .05, units='m', desc='rotor outer radius')
        self.add_input('B_g', 1.0, units='T', desc='air gap flux density')
        self.add_input('k', 0.95, desc='stacking factor')
        self.add_input('b_ry', 2.4, units='T', desc='flux density of rotor yoke')
        self.add_input('n_m', 16, desc='number of poles')
        self.add_input('t_mag', 0.005, units='m', desc='magnet thickness')
        self.add_input('b_sy', 2.4, units='T', desc='flux density of stator yoke')
        self.add_input('b_t', 2.4, units='T', desc='flux density of tooth')
        self.add_input('n_slots', 15, desc='Number of slots')
        self.add_input('n_turns', 16, desc='number of wire turns')
        self.add_input('I', 30, units='A', desc='RMS current')
        self.add_input('k_wb', 0.65, desc='bare wire slot fill factor')

        self.add_output('J', units='A/mm**2', desc='Current density')
        self.add_output('w_ry', 1.0, units='m', desc='width of stator yoke')
        self.add_output('w_sy', .005, units='m', desc='width of stator yoke')
        self.add_output('w_t', 0.010, units='m', desc='width of tooth')
        self.add_output('sta_ir', units='m', desc='stator inner radius')
        self.add_output('rot_ir', units='m', desc='rotor inner radius')
        self.add_output('s_d', units='m', desc='slot depth')
        self.add_output('slot_area', 0.0002, units='m**2', desc='area of one slot')
        self.add_output('w_slot', .01, units='m', desc='width of a slot')

        self.declare_partials('*','*', method='fd')
        #self.declare_partials('w_t', ['rot_or','B_g','n_slots','k','b_t'])
        #self.declare_partials('w_sy', ['rot_or', 'B_g', 'n_m', 'k', 'b_sy'])
        #self.declare_partials('w_ry', ['rot_or', 'B_g', 'n_m', 'k', 'b_ry'])

    def compute(self,inputs,outputs):
        radius_motor = inputs['radius_motor']  # .0765
        gap = inputs['gap']
        B_g = inputs['B_g']
        n_m = inputs['n_m']
        k = inputs['k']
        b_ry = inputs['b_ry']
        t_mag = inputs['t_mag']
        n = inputs['n_turns']
        I = inputs['I']
        k_wb = inputs['k_wb']
        b_sy= inputs['b_sy']
        n_slots = inputs['n_slots']
        b_t = inputs['b_t']
        rot_or = inputs['rot_or']

        outputs['w_ry'] = (pi*rot_or*B_g)/(n_m*k*b_ry) 
        outputs['w_t'] = (2*pi*rot_or*B_g) / (n_slots*k*b_t) 
        outputs['w_sy'] = (pi*rot_or*B_g)/(n_m*k*b_sy)
        outputs['s_d'] = radius_motor - rot_or - gap - outputs['w_sy']
        outputs['rot_ir'] = (rot_or- t_mag) - outputs['w_ry'] 
        outputs['sta_ir'] = rot_or + gap
        outputs['slot_area'] = pi/n_slots*((radius_motor**2 - (2*radius_motor*pi*rot_or*B_g)/(n_m*k*b_sy) + ((pi*rot_or*B_g)/(n_m*k*b_sy))**2) -  (rot_or**2 + 2*rot_or*gap + gap**2 ))   - ( (2*pi*rot_or*B_g)/(n_slots*k*b_t) * (radius_motor - rot_or - gap - (pi*rot_or*B_g)/(n_m*k*b_sy)) )
        outputs['w_slot'] = ( pi/n_slots*((radius_motor**2 - (2*radius_motor*pi*rot_or*B_g)/(n_m*k*b_sy) + ((pi*rot_or*B_g)/(n_m*k*b_sy))**2) -  (rot_or**2 + 2*rot_or*gap + gap**2 ))   - ( (2*pi*rot_or*B_g)/(n_slots*k*b_t) * (radius_motor - rot_or - gap - (pi*rot_or*B_g)/(n_m*k*b_sy)) ) ) / (radius_motor - rot_or - gap - ((pi*rot_or*B_g)/(n_m*k*b_sy)))         #outputs['slot_area'] / outputs['s_d']
        outputs['J'] = 2*n*I*(2.**0.5)/(k_wb*(outputs['slot_area'])*1E6)

    # def compute_partials(self, inputs, J):
    #     # Rotor Yoke Width
    #     J['w_ry', 'rot_or'] = (pi*B_g)/(n_m*k*b_ry)
    #     J['w_ry', 'B_g'] = (pi*rot_or)/(n_m*k*b_ry)
    #     J['w_ry', 'n_m'] = -(pi*rot_or*B_g)/(n_m**2*k*b_ry)
    #     J['w_ry', 'k']   = -(pi*rot_or*B_g)/(n_m*k**2*b_ry)
    #     J['w_ry', 'b_ry'] = -(pi*rot_or*B_g)/(n_m*k*b_ry**2)

    #     # Stator Yoke Width
    #     J['w_sy', 'rot_or'] = (pi*B_g)/(n_m*k*b_sy)
    #     J['w_sy', 'B_g'] = (pi*rot_or)/(n_m*k*b_sy)
    #     J['w_sy', 'n_m'] = -(pi*rot_or*B_g)/(n_m**2*k*b_sy)
    #     J['w_sy', 'k']   = -(pi*rot_or*B_g)/(n_m*k**2*b_sy)
    #     J['w_sy', 'b_sy'] = -(pi*rot_or*B_g)/(n_m*k*b_sy**2)

    #     # Tooth Width
    #     J['w_t', 'rot_or'] = (2*pi*B_g)/(n_slots*k*b_t)
    #     J['w_t', 'B_g'] = (2*pi*rot_or)/(n_slots*k*b_t)
    #     J['w_t', 'n_slots'] = -(2*pi*rot_or*B_g)/(n_slots**2*k*b_t)
    #     J['w_t', 'k']   = -(2*pi*rot_or*B_g)/(n_slots*k**2*b_t)
    #     J['w_t', 'b_t'] = -(2*pi*rt_or*B_g)/(n_slots*k*b_t**2)

    #     # Slot Depth
    #     J['s_d', 'radius_motor'] = 1 - rot_or - gap - (pi*rot_or*B_g)/(n_m*k*b_sy)
    #     J['s_d', 'rot_or'] = radius_motor - 1 - gap - (pi*B_g)/(n_m*k*b_sy)
    #     J['s_d', 'gap'] = radius_motor - rot_or - 1 - (pi*rot_or*B_g)/(n_m*k*b_sy)
    #     J['s_d', 'B_g'] = radius_motor - rot_or - gap - (pi*rot_or)/(n_m*k*b_sy)
    #     J['s_d', 'n_m'] = radius_motor - rot_or - gap + (pi*rot_or*B_g)/(n_m**2*k*b_sy)
    #     J['s_d', 'k'] = radius_motor - rot_or - gap + (pi*rot_or*B_g)/(n_m*k**2*b_sy)
    #     J['s_d', 'b_sy'] = radius_motor - rot_or - gap + (pi*rot_or*B_g)/(n_m*k*b_sy**2)

    #     #Rotor Inner Radius
    #     J['rot_ir', 'rot_or'] = (1 - t_mag) - (pi*B_g)/(n_m*k*b_ry) 
    #     J['rot_ir', 't_mag'] = (rot_or- 1) - (pi*rot_or*B_g)/(n_m*k*b_ry)   
    #     J['rot_ir', 'B_g'] = (rot_or- t_mag) - (pi*rot_or)/(n_m*k*b_ry) 
    #     J['s_d', 'n_m'] = radius_motor - rot_or - gap + (pi*rot_or*B_g)/(n_m**2*k*b_ry)
    #     J['s_d', 'k'] = radius_motor - rot_or - gap + (pi*rot_or*B_g)/(n_m*k**2*b_ry)
    #     J['s_d', 'b_ry'] = radius_motor - rot_or - gap + (pi*rot_or*B_g)/(n_m*k*b_ry**2)

    #     # Stator Inner Radius
    #     J['sta_ir', 'rot_or'] =  1 + gap
    #     J['sta_ir', 'gap'] =  rot_or + 1

    #     # Slot Area
    #     J['slot_area', 'n_slots'] = -(pi/n_slots**2)*((radius_motor**2 - (2*radius_motor*pi*rot_or*B_g)/(n_m*k*b_sy) + ((pi*rot_or*B_g)/(n_m*k*b_sy))**2) -  (rot_or**2 + 2*rot_or*gap + gap**2 ))   - ( (-2*pi*rot_or*B_g)/(n_slots**2 * k*b_t) * (radius_motor - rot_or - gap - (pi*rot_or*B_g)/(n_m*k*b_sy)) ) 
    #     J['slot_area', 'radius_motor'] = pi/n_slots*(2*radius_motor - (2*pi*rot_or*B_g)/(n_m*k*b_sy)) -  (2*pi*rot_or*B_g)/(n_slots*k*b_t)
    #     J['slot_area', 'rot_or'] = (pi/n_slots) * ( (-2*radius_motor*pi*B_g)/(n_m*k*b_sy) + 2*rot_or*pi*B_g/(n_m*k*b_sy) - (2*rot_or + 2*gap) ) - (2*pi*B_g/(n_slots*k*b_t) * (radius_motor - 2*rot_or - (2*pi*rot_or*B_g/(n_m*k*b_sy))  ) )
    #     J['slot_area', 'B_g'] = (pi/n_slots) * (  2*radius_motor*pi*rot_or/(n_m*k*b_sy) + 2*B_g*(pi*rot_or/n_m/k/b_sy)**2  ) - (  2*pi*rot_or/n_slots/k/b_t * (radius_motor - rot_or - gap - (2*pi*rot_or*B_g/n_m/k/b_sy))  )
    #     J['slot_area', 'n_m'] = (pi/n_slots) * (  (2*radius_motor*pi*rot_or*B_g)/(n_m**2 *k*b_sy) - ((pi*rot_or*B_g)/(k*b_sy))**2 * n_m**-3  ) - ((2*pi**2*rot_or**2*B_g**2)/(n_slots*k**2*b_t*b_sy*n_m**2))
    #     J['slot_area', 'k'] =   (pi/n_slots) * (  (2*radius_motor*pi*rot_or*B_g)/(n_m*k**2 *b_sy) - ((pi*rot_or*B_g)/(n_m*b_sy))**2 * k**-3  ) - ( (-2*pi*rot_or*B_g)/(n_slots*k**2 *b_t) * (radius_motor - rot_or - gap) - (4*pi**2 *rot_or**2 *B_g**2)/(n_m* k**3 *b_sy*b_t*n_slots) )
    #     J['slot_area', 'b_sy'] =  (pi/n_slots) * (  (2*radius_motor*pi*rot_or*B_g)/(n_m*k *b_sy**2) - ((pi*rot_or*B_g)/(n_m*k))**2 * b_sy**-3  ) - ( (2*pi*rot_or*B_g)/(n_slots*k*b_t) * ((pi*rot_or*B_g)/(n_m*k*b_sy**2)) )
    #     J['slot_area', 'gap'] = pi/n_slots*(-2*rot_or + 2*gap) - ( (-2*pi*rot_or*B_g)/(n_slots*k*b_t) )
    #     J['slot_area', 'b_t'] = - ( (-2*pi*rot_or*B_g)/(n_slots*k *b_t**2) * (radius_motor - rot_or - gap) - (2*pi**2 *rot_or**2 *B_g**2)/(n_m* k**2 *b_sy*b_t**2 *n_slots) )

    #     # Slot Width --- Use this for wolfram: d/dm of (((pi/l)*(  m^2 - ((2*m*pi*r*b)/(n*k*y))+ ((pi*r*b)/(n*k*y))^2 - r - 2*r*g + g^2  ))  / (m - r - g - (pi*r*b)/(n*k*y) ) ) - (   (pi/l)*(2*pi*r*b)/(l*k*t) )
        # J['w_slot', 'n_slots'] = ((4*pi**2*B_g*rot_or)/(k*n_slots**3*b_t)) - (   (pi*((pi**2*B_g**2*rot_or**2)/(k**2*n_m**2*b_sy**2) - (2*pi*B_g*radius_motor*rot_or)/(k*n_m*b_sy) + gap**2- 2*gap*rot_or + radius_motor**2 - rot_or)) / (n_slots**2 * ((-pi*B_g*rot_or)/(k*n_m*b_sy) - gap + radius_motor - rot_or))  )
        # J['w_slot', 'radius_motor'] = ( ( pi*(2*radius_motor - (2*pi*B_g*rot_or)/(k*n_m*b_sy)) )/( n_slots* ((-pi*B_g*rot_or)/(k*n_m*b_sy) - gap + radius_motor - rot_or ))  ) - (  pi*((pi**2*B_g**2*rot_or**2)/(k**2*n_m**2*b_sy**2) - (2*pi*B_g*radius_motor*rot_or)/(k*n_m*b_sy) + gap**2-2*gap*rot_or*radius_motor**2 - rot_or )/( n_slots *( (-pi*B_g*rot_or)/(k*n_m*b_sy) - gap + radius_motor - rot_or )**2 )  )
        # J['w_slot', 'rot_or'] = ((-pi*(-pi*B_g/(k*n_m*b_sy)-1) * ((pi**2*B_g**2*rot_or**2)/(k**2*n_m**2*b_sy**2) - (2*pi*B_g*radius_motor*rot_or)/(k*n_m*b_sy) + gap**2-2*gap*rot_or+radius_motor**2- rot_or)) / (n_slots*( (-pi*B_g*rot_or)/(k*n_m*b_sy)-gap+radius_motor- rot_or )**2)) + (  pi*((2*pi**2*B_g*rot_or)/(k**2*n_m**2*b_sy**2) - ((2*pi*B_g*radius_motor)/(k*n_m*b_sy) -2*gap- n_slots ) ) / (  (n_slots*((-pi*B_g*rot_or)/(k*n_m*b_sy)-gap+radius_motor- rot_or) ))) - (2*pi**2*B_g)/(k*n_slots**2*b_t)  





class MotorMassComp(om.ExplicitComponent):

    def setup(self):
        self.add_input('rho', 8110.2, units='kg/m**3', desc='density of hiperco-50')
        self.add_input('radius_motor', .075, units='m', desc='motor outer radius')           
        self.add_input('n_slots', 15, desc='number of slots')                           
        self.add_input('sta_ir', .06225, units='m', desc='stator inner radius')       
        self.add_input('w_t', units='m', desc='tooth width')                        
        self.add_input('stack_length', units='m', desc='length of stack')  
        self.add_input('s_d', units='m', desc='slot depth')                         
        self.add_input('rot_or', 0.0615, units='m', desc='rotor outer radius')
        self.add_input('rot_ir', 0.0515, units='m', desc='rotor inner radius')
        self.add_input('t_mag', .005, units='m', desc='magnet thickness')
        self.add_input('rho_mag', 7500, units='kg/m**3', desc='density of magnet')

        self.add_output('mag_mass', 0.5, units='kg', desc='mass of magnets')
        self.add_output('sta_mass', 25, units='kg', desc='mass of stator')
        self.add_output('rot_mass', 1.0, units='kg', desc='weight of rotor')
        self.add_output('motor_mass', 2, units='kg', desc='total mass of motor')
        
        self.declare_partials('*','*', method='fd')

    def compute(self,inputs,outputs):
        rho=inputs['rho']
        radius_motor=inputs['radius_motor']
        n_slots=inputs['n_slots']
        sta_ir=inputs['sta_ir']
        w_t=inputs['w_t']
        stack_length=inputs['stack_length']
        s_d=inputs['s_d']
        rot_ir=inputs['rot_ir']
        rot_or=inputs['rot_or']
        stack_length=inputs['stack_length']
        t_mag=inputs['t_mag']
        rho_mag=inputs['rho_mag']

        outputs['sta_mass'] = rho * stack_length * ((pi * radius_motor**2)-(pi * (sta_ir+s_d)**2)+(n_slots*(w_t*s_d)))
        outputs['rot_mass'] = (pi*(rot_or - t_mag)**2 - pi*rot_ir**2) * rho * stack_length
        outputs['mag_mass'] = (((pi*rot_or**2) - (pi*(rot_or-t_mag)**2))) * rho_mag * stack_length
        outputs['motor_mass'] = outputs['sta_mass'] + outputs['rot_mass'] + outputs['mag_mass']

    # def compute_partials(self,inputs,J):

        # stator
    #   rho=inputs['rho']
    #   radius_motor=inputs['radius_motor']
    #   n_slots=inputs['n_slots']
    #   sta_ir=inputs['sta_ir']
    #   w_t=inputs['w_t']
    #   stack_length=inputs['stack_length']

    #   J['sta_mass', 'rho'] = 
    #   J['sta_mass', 'radius_motor'] = 
    #   J['sta_mass', 'n_slots'] = 
    #   J['sta_mass', 'sta_ir'] = 
    #   J['sta_mass', 'w_t'] = 
    #   J['sta_mass', 'stack_length'] = 

# ---------------------------------------      
 
