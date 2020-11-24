from optimizer2 import main as optimize
from createDat import main as createDat

optimize()
createDat()

ampl_mod_command = "model 'C:\Users\Shaurya\Desktop\math187 project\amplFiles\model.mod'; "

ampl_dat_command = "data 'C:\Users\Shaurya\Desktop\math187 project\amplFiles\test1.dat';"

ampl_solve_command = "solve;"

ample_option_command = "option omit_zero_rows 1;"

ampl_display_command = "display x;"

ampl_all_commands = ampl_mod_command + ampl_dat_command + ampl_solve_command + ample_option_command + ampl_display_command

print(ampl_all_commands)