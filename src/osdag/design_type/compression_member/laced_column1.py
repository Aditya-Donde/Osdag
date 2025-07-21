"""
Main module: Design of Laced Column
Sub-module:  Design of laced column (compound column)

@author: [Your Name]

Reference:
    1) IS 800: 2007 General construction in steel - Code of practice (Third revision)

"""
import logging
import math
import numpy as np
from ...Common import *
# Removed moment_connection import to avoid dependency issues
# from ..connection.moment_connection import MomentConnection
from ...utils.common.material import *
from ...utils.common.load import Load
from ...utils.common.component import ISection, Material
from ...utils.common.component import *
from ..member import Member
# Removed report_functions import to avoid dependency issues
# from ...Report_functions import *
# Removed pylatex imports to avoid dependency issues
# from ...design_report.reportGenerator_latex import CreateLatex
# from pylatex.utils import NoEscape
from .compression import Compression

class LacedColumn(Compression):
    """
    Class for the design of laced (compound) columns as per IS 800:2007
    """
    def __init__(self):
        super().__init__()
        # Additional initialization for laced columns can go here
        # These attributes are required for section classification and effective length calculations
        self.length_zz = None  # To be set via set_input_values
        self.end_1_z = None
        self.end_2_z = None
        self.length_yy = None
        self.end_1_y = None
        self.end_2_y = None

    def tab_list(self):
        """Return the list of tuples for design preference tabs."""
        pass

    def tab_value_changed(self):
        """Update values of keys in design preferences dependent on other inputs."""
        pass

    def edit_tabs(self):
        """Return a list for dynamic tab names if needed."""
        pass

    def input_dictionary_design_pref(self):
        """Return list of tuples for design preferences to be saved to design dictionary."""
        pass

    def input_dictionary_without_design_pref(self):
        """Return list of tuples for default design preferences if not set by user."""
        pass

    def refresh_input_dock(self):
        """Return list of tuples for keys to be updated on changing design preferences."""
        pass

    def get_values_for_design_pref(self, key, design_dictionary):
        """Return value for a given design preference key."""
        pass

    def input_values(self):
        """Return a list of tuples for the UI (Input Dock) for laced column design."""
        pass

    def set_input_values(self, design_dictionary):
        """Set input values from the design dictionary for laced column design."""
        super(LacedColumn, self).set_input_values(design_dictionary)

        # section properties
        self.module = design_dictionary[KEY_MODULE]
        self.mainmodule = 'Laced Column Design'
        self.sec_profile = design_dictionary[KEY_SEC_PROFILE]
        self.sec_list = design_dictionary[KEY_SECSIZE]
        self.material = design_dictionary[KEY_SEC_MATERIAL]

        # section user data
        self.length_zz = float(design_dictionary[KEY_UNSUPPORTED_LEN_ZZ])
        self.length_yy = float(design_dictionary[KEY_UNSUPPORTED_LEN_YY])

        # end condition
        self.end_1_z = design_dictionary[KEY_END1]
        self.end_2_z = design_dictionary[KEY_END2]

        self.end_1_y = design_dictionary[KEY_END1_Y]
        self.end_2_y = design_dictionary[KEY_END2_Y]

        # factored loads
        self.load = Load(axial_force=design_dictionary[KEY_AXIAL], shear_force=0.0, moment=0.0, moment_minor=0.0, unit_kNm=True)

        # design preferences
        self.allowable_utilization_ratio = float(design_dictionary[KEY_ALLOW_UR])
        self.effective_area_factor = float(design_dictionary[KEY_EFFECTIVE_AREA_PARA])

        #TODO: @danish this should be handeled dynamically at run-time
        try:
            self.optimization_parameter = design_dictionary[KEY_OPTIMIZATION_PARA]
        except:
            self.optimization_parameter = 'Utilization Ratio'
        # self.allow_class1 = design_dictionary[KEY_ALLOW_CLASS1]
        # self.allow_class2 = design_dictionary[KEY_ALLOW_CLASS2]
        # self.allow_class3 = design_dictionary[KEY_ALLOW_CLASS3]
        # self.allow_class4 = design_dictionary[KEY_ALLOW_CLASS4]
        try:
            self.steel_cost_per_kg = float(design_dictionary[KEY_STEEL_COST])
        except:
            self.steel_cost_per_kg = 50

        # Initialize material property
        self.material_property = Material(self.material)

        # Initialize allowed sections based on design preferences
        self.allowed_sections = []
        try:
            if design_dictionary[KEY_ALLOW_CLASS1]:
                self.allowed_sections.append('Plastic')
        except:
            pass
        try:
            if design_dictionary[KEY_ALLOW_CLASS2]:
                self.allowed_sections.append('Compact')
        except:
            pass
        try:
            if design_dictionary[KEY_ALLOW_CLASS3]:
                self.allowed_sections.append('Semi-Compact')
        except:
            pass
        try:
            if design_dictionary[KEY_ALLOW_CLASS4]:
                self.allowed_sections.append('Slender')
        except:
            pass

        # If no sections are allowed, default to all
        if len(self.allowed_sections) == 0:
            self.allowed_sections = ['Plastic', 'Compact', 'Semi-Compact', 'Slender']

        # Initialize design status
        self.design_status = False
        self.failed_design_dict = {}
        # flag = self.section_classification()
        # print(f"Section classification result: {flag}")
        # if flag:
        #     self.design_laced_column()
        #     self.results()
        # print(f"Here[LacedColumn/set_input_values]")

    # def section_classification(self):
    #     """Classify the sections for laced column as per IS 800:2007."""
    #     ...  # (existing code commented out)

    def calculate_spacing(self, I_yy, I_zz, A, C_yy, placement='back-to-back'):
        """
        Calculate the spacing S between the members of a compound column (channels).
        Args:
            I_yy: Moment of inertia along the major axis
            I_zz: Moment of inertia along the minor axis
            A: Area of one channel
            C_yy: Centre of gravity for channels
            placement: 'back-to-back' or 'toe-to-toe'
        Returns:
            S: Spacing between two members (rounded up to nearest 10 for toe-to-toe)
        """
        import math
        if placement == 'back-to-back':
            # 2 * [I_yy + A * (S/2 + C_yy)^2] = 2 * I_zz
            # I_yy + A * (S/2 + C_yy)^2 = I_zz
            # (S/2 + C_yy)^2 = (I_zz - I_yy) / A
            # S/2 + C_yy = sqrt((I_zz - I_yy) / A)
            # S = 2 * (sqrt((I_zz - I_yy) / A) - C_yy)
            root = (I_zz - I_yy) / A
            if root < 0:
                raise ValueError("Invalid input: (I_zz - I_yy) / A is negative.")
            S = 2 * (math.sqrt(root) - C_yy)
            if S < 0:
                raise ValueError("Calculated spacing S is negative. Check your input values.")
            return S
        elif placement == 'toe-to-toe':
            # 2 * [I_yy + A * (S/2 - C_yy)^2] = 2 * I_zz
            # I_yy + A * (S/2 - C_yy)^2 = I_zz
            # (S/2 - C_yy)^2 = (I_zz - I_yy) / A
            # S/2 - C_yy = sqrt((I_zz - I_yy) / A)
            # S = 2 * (sqrt((I_zz - I_yy) / A) + C_yy)
            root = (I_zz - I_yy) / A
            if root < 0:
                raise ValueError("Invalid input: (I_zz - I_yy) / A is negative.")
            S = 2 * (math.sqrt(root) + C_yy)
            # Round up to nearest 10
            S = int(math.ceil(S / 10.0)) * 10
            if S < 0:
                raise ValueError("Calculated spacing S is negative. Check your input values.")
            return S
        else:
            raise ValueError("placement must be 'back-to-back' or 'toe-to-toe'")

    def design_laced_column(self):
        """Perform the design of the laced column."""
        pass

    def results(self):
        """Compile and store the results of the laced column design."""
        pass

    def common_result(self, list_result, result_type):
        """Process and store common results for the laced column design."""
        pass

    def save_design(self, popup_summary):
        """Save the design and generate reports for the laced column."""
        pass

    def design_tie_plate(self, S, C_yy, b_f, g, placement='back-to-back'):
        """
        Design the tie plate for laced columns as per IS 800:2007 (see image for formulas).
        Args:
            S: Spacing between the compound columns (mm)
            C_yy: Centre of gravity for channels (mm)
            b_f: Flange width (mm)
            g: Gauge distance as per IS:808 steel table (mm)
            placement: 'back-to-back' or 'toe-to-toe'
        Returns:
            dict with keys: De, D, L, t
        """
        import math
        result = {}
        if placement == 'back-to-back':
            # De = S + 2 * C_yy >= 2 * b_f
            De = S + 2 * C_yy
            min_De = 2 * b_f
            if De < min_De:
                print(f"Warning: De ({De}) is less than 2*b_f ({min_De})")
            # D = De + 2 * g
            D = De + 2 * g
        elif placement == 'toe-to-toe':
            # De = S - 2 * C_yy
            De = S - 2 * C_yy
            # D = De + 2 * g
            D = De + 2 * g
        else:
            raise ValueError("placement must be 'back-to-back' or 'toe-to-toe'")
        # L = S + 2 * g
        L = S + 2 * g
        # t = (1/50) * (S + 2 * g)
        t = (1/50) * (S + 2 * g)
        # Round De, D, L to next higher multiple of 25 as per code
        def round_up_25(x):
            return int(math.ceil(x / 25.0)) * 25
        De_rounded = round_up_25(De)
        D_rounded = round_up_25(D)
        L_rounded = round_up_25(L)
        t_rounded = round(t, 2)
        result['De'] = De_rounded
        result['D'] = D_rounded
        result['L'] = L_rounded
        result['t'] = t_rounded
        return result

    def design_lacing(self, S, g, L, D_t):
        """
        Design the lacing system for a laced column as per IS 800:2007.
        Args:
            S: Spacing between the members (mm)
            g: Gauge distance (mm)
            L: Length of column (mm)
            D_t: Depth of tie plate (mm)
        Returns:
            dict with keys: L0i, N_L, L0, theta_deg, angle_ok
        """
        return self._calculate_lacing_spacing(S, g, L, D_t)

    def _calculate_lacing_spacing(self, S, g, L, D_t):
        import math
        # Step 1: Initial spacing
        L0i = 2 * (S + 2 * g)  # cot(45) = 1

        # Step 2: Number of lacings
        N_L = (L - 2 * D_t - 4 * 20) / L0i + 1
        N_L = int(round(N_L))

        # Step 3: Actual spacing
        if N_L > 1:
            L0 = (L - 2 * D_t - 4 * 20) / (N_L - 1)
        else:
            L0 = L0i

        # Step 4: Angle
        denominator = 2 * (S + 2 * g)
        if denominator == 0:
            theta_deg = None
            angle_ok = False
        else:
            theta_rad = math.atan(denominator / L0)
            theta_deg = math.degrees(math.atan(denominator / L0))
            # But formula is cot^-1(L0/denominator)
            theta_deg = math.degrees(math.atan(denominator / L0))
            # Or, equivalently:
            # theta_deg = math.degrees(math.acot(L0 / denominator))
            # But Python does not have acot, so use atan(denominator / L0)
            angle_ok = 40 < theta_deg < 70

        return {
            "L0i": L0i,
            "N_L": N_L,
            "L0": L0,
            "theta_deg": theta_deg,
            "angle_ok": angle_ok
        }

    def check_lacing_slenderness(self, L0, r_min, lambda_e):
        """
        Check the slenderness ratio of lacings as per IS 800:2007 Cl. 7.6.5.1.
        Args:
            L0: Spacing between lacings (mm)
            r_min: Minimum radius of gyration of the main member (mm)
            lambda_e: Effective slenderness ratio of the main member
        Returns:
            dict with keys:
                slenderness_ratio: L0 / r_min
                slenderness_limit: min(50, 0.7 * lambda_e)
                is_ok: True if slenderness_ratio <= slenderness_limit, else False
        """
        slenderness_ratio = L0 / r_min
        slenderness_limit = min(50, 0.7 * lambda_e)
        is_ok = slenderness_ratio <= slenderness_limit
        return {
            "slenderness_ratio": slenderness_ratio,
            "slenderness_limit": slenderness_limit,
            "is_ok": is_ok
        }

    def design_single_lacing(self, AF, theta_deg, N=1):
        """
        Design the lacing for a single-laced column as per IS 800:2007 Cl. 7.6.6.1.
        Args:
            AF: Factored axial force (same units throughout)
            theta_deg: Angle of lacing in degrees
            N: Number of lacing planes (default 1 for single-laced)
        Returns:
            dict with keys:
                Vt: Total transverse shear to be resisted by lacing (same units as AF)
                Vt_per_lacing: Shear per lacing (same units as AF)
                Pcal: Compressive force in lacing (same units as AF)
        """
        import math
        Vt = 0.025 * AF
        Vt_per_lacing = Vt / N
        theta_rad = math.radians(theta_deg)
        if math.sin(theta_rad) == 0:
            raise ValueError("Theta cannot be 0 or 180 degrees for csc(theta)")
        Pcal = Vt_per_lacing / math.sin(theta_rad)
        return {
            "Vt": Vt,
            "Vt_per_lacing": Vt_per_lacing,
            "Pcal": Pcal
        }

def lacing_flat_size(S, g, lacing_type='single'):
    """
    Calculate the effective length, max thickness, and min radius of gyration for a lacing flat as per IS 800:2007 Cl. 7.6.3.

    Args:
        S (float): Spacing between members (mm)
        g (float): Gauge length (mm)
        lacing_type (str): 'single' or 'double'

    Returns:
        dict: {
            'effective_length': float,
            'max_thickness': float,
            'min_radius_of_gyration': float
        }
    """
    import math

    # Effective length (Eq. 2.25)
    effective_length = S + 2 * g / math.sin(math.radians(45))  # csc(45) = 1/sin(45)
    # Or, since csc(45) = sqrt(2), so:
    # effective_length = S + 2 * g * math.sqrt(2)

    # Max thickness (Eq. 2.26, 2.27)
    if lacing_type == 'single':
        max_thickness = (1/40) * effective_length
    elif lacing_type == 'double':
        max_thickness = (1/60) * effective_length
    else:
        raise ValueError("lacing_type must be 'single' or 'double'")

    # Min radius of gyration (Eq. 2.28)
    min_radius_of_gyration = max_thickness / math.sqrt(12)

    return {
        'effective_length': effective_length,
        'max_thickness': max_thickness,
        'min_radius_of_gyration': min_radius_of_gyration
    }

def lacing_design_strength_check(
    effective_length, t, A_g, f_y, f_u, E, P_act, lacing_type='flat', 
    L_c=None, w=None, t_leg=None, A_nc=None, gamma_m0=1.1, gamma_m1=1.25
):
    """
    Check the design strength of lacing (compression and tension) as per IS 800:2007.

    Args:
        effective_length (float): Effective length of lacing (mm)
        t (float): Thickness of lacing (mm)
        A_g (float): Gross area of lacing (mm^2)
        f_y (float): Yield strength (MPa)
        f_u (float): Ultimate strength (MPa)
        E (float): Young's modulus (MPa)
        P_act (float): Actual force in lacing (N)
        lacing_type (str): 'flat', 'angle', or 'channel'
        L_c (float): Length of connection (for rupture, mm)
        w (float): Outstand leg width (for rupture, mm)
        t_leg (float): Thickness of outstand leg (for rupture, mm)
        A_nc (float): Net area at critical section (for rupture, mm^2)
        gamma_m0 (float): Partial safety factor for yield
        gamma_m1 (float): Partial safety factor for ultimate

    Returns:
        dict: {
            'lambda_e': ...,
            'f_cd': ...,
            'P_d': ...,
            'T_dg': ...,
            'T_dn': ...,
            'is_compression_safe': ...,
            'is_tension_yield_safe': ...,
            'is_tension_rupture_safe': ...
        }
    """
    import math

    # 1. Slenderness ratio
    r_min = t / math.sqrt(12)
    lambda_e = effective_length / r_min

    # 2. Non-dimensional slenderness
    f_cc = (math.pi ** 2 * E) / (lambda_e ** 2)
    lambda_bar = math.sqrt(f_y / f_cc)

    # 3. Imperfection factor (a): for flats/angles, use a=0.49 (Class c, IS 800 Table 7)
    a = 0.49

    # 4. Phi
    phi = 0.5 * (1 + a * (lambda_bar - 0.2) + lambda_bar ** 2)

    # 5. Stress reduction factor (chi)
    chi = 1 / (phi + math.sqrt(phi ** 2 - lambda_bar ** 2))

    # 6. Design compressive stress
    f_cd = min(chi * f_y / gamma_m0, f_y / gamma_m0)

    # 7. Compressive strength
    P_d = A_g * f_cd

    # 8. Tension strength (yielding)
    T_dg = A_g * f_y / gamma_m0

    # 9. Tension strength (rupture)
    if A_nc is not None:
        # Shear lag factor β
        if lacing_type == 'angle' and w is not None and t_leg is not None and L_c is not None:
            beta = 1.4 - 0.076 * (w / (t_leg * L_c))
            beta = min(max(beta, 0.7), 0.9 * f_y * gamma_m1 / (f_u * gamma_m0))
        else:
            beta = 1.0
        T_dn = 0.9 * A_nc * f_u / gamma_m1 + beta * A_g * f_y / gamma_m0
    else:
        T_dn = None

    # Safety checks
    is_compression_safe = P_d >= P_act
    is_tension_yield_safe = T_dg >= P_act
    is_tension_rupture_safe = T_dn is None or T_dn >= P_act

    return {
        'lambda_e': lambda_e,
        'f_cd': f_cd,
        'P_d': P_d,
        'T_dg': T_dg,
        'T_dn': T_dn,
        'is_compression_safe': is_compression_safe,
        'is_tension_yield_safe': is_tension_yield_safe,
        'is_tension_rupture_safe': is_tension_rupture_safe
    }

# Test section for debugging
def test_tie_plate():
    print("\nTesting LacedColumn tie plate design...")
    laced_column = LacedColumn()
    # Example values (replace with real values as needed)
    S = 300  # mm (spacing between columns)
    C_yy = 40  # mm
    b_f = 100  # mm (flange width)
    g = 70    # mm (gauge distance)
    print("Back-to-back tie plate:")
    res_back = laced_column.design_tie_plate(S, C_yy, b_f, g, placement='back-to-back')
    print(f"  De = {res_back['De']} mm (rounded)")
    print(f"  D  = {res_back['D']} mm (rounded)")
    print(f"  L  = {res_back['L']} mm (rounded)")
    print(f"  t  = {res_back['t']} mm")
    print("Toe-to-toe tie plate:")
    res_toe = laced_column.design_tie_plate(S, C_yy, b_f, g, placement='toe-to-toe')
    print(f"  De = {res_toe['De']} mm (rounded)")
    print(f"  D  = {res_toe['D']} mm (rounded)")
    print(f"  L  = {res_toe['L']} mm (rounded)")
    print(f"  t  = {res_toe['t']} mm")

if __name__ == "__main__":
    print("Minimal test for LacedColumn spacing and tie plate design...")
    laced_column = LacedColumn()
    # Hardcoded test values
    I_yy = 500000  # mm^4
    I_zz = 800000  # mm^4
    A = 2000       # mm^2
    C_yy = 40      # mm
    b_f = 100      # mm (flange width)
    g = 70         # mm (gauge distance)

    # Test spacing calculation
    try:
        S_back = laced_column.calculate_spacing(I_yy, I_zz, A, C_yy, placement='back-to-back')
        print(f"Back-to-back spacing: S = {S_back:.2f} mm")
    except Exception as e:
        print(f"Back-to-back spacing error: {e}")
    try:
        S_toe = laced_column.calculate_spacing(I_yy, I_zz, A, C_yy, placement='toe-to-toe')
        print(f"Toe-to-toe spacing: S = {S_toe} mm (rounded up to nearest 10)")
    except Exception as e:
        print(f"Toe-to-toe spacing error: {e}")

    # Test tie plate design (use S_toe for demonstration)
    try:
        res_back = laced_column.design_tie_plate(S=300, C_yy=C_yy, b_f=b_f, g=g, placement='back-to-back')
        print("Back-to-back tie plate:")
        print(f"  De = {res_back['De']} mm (rounded)")
        print(f"  D  = {res_back['D']} mm (rounded)")
        print(f"  L  = {res_back['L']} mm (rounded)")
        print(f"  t  = {res_back['t']} mm")
        res_toe = laced_column.design_tie_plate(S=300, C_yy=C_yy, b_f=b_f, g=g, placement='toe-to-toe')
        print("Toe-to-toe tie plate:")
        print(f"  De = {res_toe['De']} mm (rounded)")
        print(f"  D  = {res_toe['D']} mm (rounded)")
        print(f"  L  = {res_toe['L']} mm (rounded)")
        print(f"  t  = {res_toe['t']} mm")
    except Exception as e:
        print(f"Tie plate design error: {e}")

    print("\nTesting lacing design...")
    S = 300
    g = 70
    L = 5000
    D_t = 12
    lacing_result = laced_column.design_lacing(S, g, L, D_t)
    print("Lacing design results:")
    for k, v in lacing_result.items():
        print(f"  {k}: {v}")

    print("\nTesting lacing slenderness check...")
    # Example values (replace with real values as needed)
    L0 = lacing_result["L0"]
    r_min = 25  # mm (example)
    lambda_e = 80  # (example)
    slenderness_result = laced_column.check_lacing_slenderness(L0, r_min, lambda_e)
    print("Lacing slenderness check results:")
    for k, v in slenderness_result.items():
        print(f"  {k}: {v}")

    print("\nTesting single-laced column design...")
    AF = 1000  # Example factored axial force (kN or N, be consistent)
    theta_deg = lacing_result["theta_deg"]  # Use calculated theta from lacing spacing
    single_lacing_result = laced_column.design_single_lacing(AF, theta_deg)
    print("Single-laced column design results:")
    for k, v in single_lacing_result.items():
        print(f"  {k}: {v:.2f}")

    # Example usage:
    S = 300  # mm
    g = 70   # mm

    result_single = lacing_flat_size(S, g, lacing_type='single')
    result_double = lacing_flat_size(S, g, lacing_type='double')

    print("Single-laced:", result_single)
    print("Double-laced:", result_double)

    # Example values (replace with your actual design values)
    result = lacing_design_strength_check(
        effective_length=500,  # mm
        t=8,                   # mm
        A_g=400,               # mm^2
        f_y=250,               # MPa
        f_u=410,               # MPa
        E=2e5,                 # MPa
        P_act=20000            # N
    )
    print(result)



    
