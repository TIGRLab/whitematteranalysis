#!/Library/Frameworks/EPD64.framework/Versions/Current/bin/ipython

# Run registration on the test dataset.

import os
import glob
import matplotlib.pyplot as plt
import numpy
import time
import multiprocessing
import argparse

import vtk

try:
    import whitematteranalysis as wma
except:
    print "<wm_register.py> Error importing white matter analysis package\n"
    raise

# defaults that may be added as parameters later
#fiber_sample_sizes = [25, 50, 75, 100]
#fiber_sample_sizes = [50, 150, 200, 200]
fiber_sample_fractions = [.10, .20, .30, .40]
sigma_per_scale = [30, 10, 10, 5]
steps_per_scale=[10, 3, 2, 2]
#steps_per_scale=[1, 1, 1, 1]
fibers_rendered = 100

# figure out how many cobyla iterations are needed
# this is reasonable for two subjects
#maxfun_per_scale = [20, 40, 60, 80]


#-----------------
# Parse arguments
#-----------------
parser = argparse.ArgumentParser(
    description="Runs multisubject unbiased group registration of tractography.",
    epilog="Written by Lauren O\'Donnell, odonnell@bwh.harvard.edu.  Please reference \"Unbiased Groupwise Registration of White Matter Tractography. LJ O'Donnell,  WM Wells III, Golby AJ, CF Westin. Med Image Comput Comput Assist Interv. 2012;15(Pt 3):123-30.\"",
    version='1.0')

parser.add_argument(
    'inputDirectory',
    help='A directory of whole-brain tractography as vtkPolyData (.vtk or .vtp).')
parser.add_argument(
    'outputDirectory',
    help='The output directory will be created if it does not exist.')
parser.add_argument(
    '-f', action="store", dest="numberOfFibers", type=int,
    help='Number of fibers to analyze from each dataset. 300-600 or more is reasonable. Depends on total number of datasets and desired run time/memory use.')
parser.add_argument(
    '-l', action="store", dest="fiberLength", type=int,
    help='Minimum length (in mm) of fibers to analyze. 60mm is default.')
parser.add_argument(
    '-j', action="store", dest="numberOfJobs", type=int,
    help='Number of processors to use.')
parser.add_argument(
    '-verbose', action='store_true', dest="flag_verbose",
    help='Verbose. Run with -verbose to store images of intermediate and final polydatas.')
parser.add_argument(
    '-pf', action="store", dest="pointsPerFiber", type=int,
    help='Number of points for fiber representation during registration. 5 is reasonable, or more.')

 
args = parser.parse_args()

print "\n\n<register> =========GROUP REGISTRATION============"
print "<register> Performing unbiased group registration."
print "<register> Input  directory: ", args.inputDirectory
print "<register> Output directory: ", args.outputDirectory
print "\n<register> ============PARAMETERS================="

if not os.path.isdir(args.inputDirectory):
    print "<register> Error: Input directory", args.inputDirectory, "does not exist."
    exit()

outdir = args.outputDirectory
if not os.path.exists(outdir):
    print "<register> Output directory", outdir, "does not exist, creating it."
    os.makedirs(outdir)

if args.numberOfFibers is not None:
    number_of_fibers = args.numberOfFibers
else:
    number_of_fibers = 300
print "<register> Number of fibers to analyze per subject: ", number_of_fibers

if args.fiberLength is not None:
    fiber_length = args.fiberLength
else:
    fiber_length = 75
print "<register> Minimum length of fibers to analyze (in mm): ", fiber_length
    
if args.numberOfJobs is not None:
    parallel_jobs = args.numberOfJobs
else:
    parallel_jobs = multiprocessing.cpu_count()
print "<register> CPUs detected:", multiprocessing.cpu_count(), ". Number of jobs to use:", parallel_jobs

if args.flag_verbose:
    print "<register> Verbose display and intermediate image saving ON."
else:
    print "<register> Verbose display and intermediate image saving OFF."
verbose = args.flag_verbose

if args.pointsPerFiber is not None:
    points_per_fiber = args.pointsPerFiber
else:
    points_per_fiber = 5
print "<register> Number of points for fiber representation: ", points_per_fiber


print "\n<register> Starting registration...\n"


def compute_multiscale_registration(register, scale_mode, n_steps, fiber_sample_size, sigma, maxfun):

    print "<register> SCALE:", scale_mode, "SIGMA:", sigma, "SAMPLES:", fiber_sample_size, "MAXFUN:", maxfun

    register.fiber_sample_size = fiber_sample_size
    register.sigma = sigma
    register.maxfun = maxfun
    
    if scale_mode == "Coarse":
        # relatively large steps
        inc_rot = (5.0 / 180.0) * numpy.pi
        inc_trans = 5.0
        inc_scale = 0.01
        inc_shear = (2.0 / 180.0) * numpy.pi
        register.set_rhobeg(inc_rot, inc_trans, inc_scale, inc_shear)    
        # relatively easy threshold to converge
        inc_rot = (4.5 / 180.0) * numpy.pi
        inc_trans = 4.5
        inc_scale = 0.01
        inc_shear = (2.0 / 180.0) * numpy.pi        
        register.set_rhoend(inc_rot, inc_trans, inc_scale, inc_shear)    
        # n = 5
        # only translation and rotation. initialization.
        for idx in range(0, n_steps):
            print "<register> SCALE:", scale_mode, idx+1, "/", n_steps
            register.translate_only()
            register.compute()
            register.rotate_only()
            register.compute()
    elif scale_mode == "Medium":
        # medium steps
        inc_rot = (4.0 / 180.0) * numpy.pi
        inc_trans = 4.0
        inc_scale = 0.01
        inc_shear = (2.0 / 180.0) * numpy.pi
        register.set_rhobeg(inc_rot, inc_trans, inc_scale, inc_shear)    
        # relatively easy threshold to converge
        inc_rot = (3.0 / 180.0) * numpy.pi
        inc_trans = 3.0
        inc_scale = 0.008
        inc_shear = (1.5 / 180.0) * numpy.pi        
        register.set_rhoend(inc_rot, inc_trans, inc_scale, inc_shear)    
        # n = 1
        for idx in range(0, n_steps):
            print "<register> SCALE:", scale_mode, idx+1, "/", n_steps
            register.translate_only()
            register.compute()
            register.rotate_only()
            register.compute()
            register.scale_only()
            register.compute()
            register.shear_only()
            register.compute()
    elif scale_mode == "Fine":
        # finer steps
        inc_rot = (3.0 / 180.0) * numpy.pi
        inc_trans = 3.0
        inc_scale = 0.008
        inc_shear = (1.5 / 180.0) * numpy.pi        
        register.set_rhobeg(inc_rot, inc_trans, inc_scale, inc_shear)    
        # smaller threshold to converge
        inc_rot = (2.0 / 180.0) * numpy.pi
        inc_trans = 2.0
        inc_scale = 0.006
        inc_shear = (1.0 / 180.0) * numpy.pi        
        register.set_rhoend(inc_rot, inc_trans, inc_scale, inc_shear)    
        # n = 1
        for idx in range(0, n_steps):
            print "<register> SCALE:", scale_mode, idx+1, "/", n_steps
            register.translate_only()
            register.compute()
            register.rotate_only()
            register.compute()
            register.scale_only()
            register.compute()
            register.shear_only()
            register.compute()
    elif scale_mode == "Finest":
        inc_rot = (1.0 / 180.0) * numpy.pi
        inc_trans = 1.0
        inc_scale = 0.005
        inc_shear = (1.0 / 180.0) * numpy.pi
        register.set_rhobeg(inc_rot, inc_trans, inc_scale, inc_shear)
        inc_rot = (0.5 / 180.0) * numpy.pi
        inc_trans = 0.5
        inc_scale = 0.001
        inc_shear = (0.75 / 180.0) * numpy.pi
        register.set_rhoend(inc_rot, inc_trans, inc_scale, inc_shear)    
        # n = 1
        for idx in range(0, n_steps):
            print "<register> SCALE:", scale_mode, idx+1, "/", n_steps
            register.translate_only()
            register.compute()
            register.rotate_only()
            register.compute()
            register.scale_only()
            register.compute()
            register.shear_only()
            register.compute()
            
    
def run_registration(input_directory, outdir, number_of_fibers=150,
                     fiber_sample_fractions=[.10, .20, .30, .40],
                     parallel_jobs=2,
                     points_per_fiber=5,
                     sigma_per_scale=[30, 10, 10, 5],
                     maxfun_per_scale=None,
                     distance_method='Hausdorff', 
                     verbose=True, 
                     fiber_length=75,
                     fibers_rendered=100,
                     steps_per_scale=[10, 3, 2, 2]):

    elapsed = list()

    input_pds, subject_ids = wma.io.read_and_preprocess_polydata_directory(input_directory, fiber_length, number_of_fibers)

    number_of_datasets = len(input_pds)
    
    # figure out maximum function evals for optimizer if not requested
    if maxfun_per_scale is None:
        # figure out how many cobyla iterations are needed
        minfun = number_of_datasets 
        maxfun_per_scale = [minfun*10, minfun*10, minfun*15, minfun*30]        

    # figure out numbers of fibers to sample
    fiber_sample_sizes = (number_of_fibers * numpy.array(fiber_sample_fractions)).astype(int)

    # create registration object and apply settings
    register = wma.congeal.CongealTractography()
    register.parallel_jobs = parallel_jobs
    register.threshold = 0
    register.points_per_fiber = points_per_fiber
    register.distance_method = distance_method
    
    # add inputs to the registration
    for pd in input_pds:
        register.add_subject(pd)

    # view output data from the initialization
    outdir_current =  os.path.join(outdir, 'iteration_0')
    if not os.path.exists(outdir_current):
        os.makedirs(outdir_current)
    output_pds = wma.registration_functions.transform_polydatas(input_pds, register)
    # save the current atlas representation to disk
    wma.registration_functions.save_atlas(output_pds, outdir_current)
    # save pictures of the current 'atlas' or registered data
    ren = wma.registration_functions.view_polydatas(output_pds, fibers_rendered)
    ren.save_views(outdir_current)
    del ren
    wma.registration_functions.write_transforms_to_itk_format(register.convert_transforms_to_vtk(), outdir_current)
    
    scales = ["Coarse", "Medium", "Fine", "Finest"]
    scale_idx = 0
    for scale in scales:
        start = time.time()
        # run the basic iteration of translate, rotate, scale
        compute_multiscale_registration(register, scale, steps_per_scale[scale_idx], fiber_sample_sizes[scale_idx], sigma_per_scale[scale_idx], maxfun_per_scale[scale_idx])
        elapsed.append(time.time() - start)
        scale_idx += 1
        
        # view output data from this big iteration
        if verbose | (scale == "Finest"):
            outdir_current =  os.path.join(outdir, 'iteration_'+str(scale_idx))
            if not os.path.exists(outdir_current):
                os.makedirs(outdir_current)
            output_pds = wma.registration_functions.transform_polydatas(input_pds, register)
            # save the current atlas representation to disk
            wma.registration_functions.save_atlas(output_pds, outdir_current)
            # save pictures of the current 'atlas' or registered data
            ren = wma.registration_functions.view_polydatas(output_pds, fibers_rendered)
            ren.save_views(outdir_current)
            del ren
            if scale == "Finest":
                wma.registration_functions.transform_polydatas_from_disk(input_directory, register, outdir_current)
            wma.registration_functions.write_transforms_to_itk_format(register.convert_transforms_to_vtk(), outdir_current)
    
            plt.figure() # to avoid all results on same plot
            plt.plot(range(len(register.objective_function_values)), register.objective_function_values)
            plt.savefig(os.path.join(outdir_current, 'objective_function.pdf'))
        
    return register, elapsed


## run the registration ONCE and output result to disk
register, elapsed = run_registration(args.inputDirectory, outdir,
                                     number_of_fibers=number_of_fibers,
                                     points_per_fiber=points_per_fiber,
                                     parallel_jobs=parallel_jobs,
                                     fiber_sample_fractions=fiber_sample_fractions,
                                     sigma_per_scale=sigma_per_scale,
                                     verbose=verbose,
                                     fiber_length=fiber_length,
                                     fibers_rendered=fibers_rendered,
                                     steps_per_scale=steps_per_scale)

print "TIME:", elapsed
