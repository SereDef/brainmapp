import os
import pandas as pd
import numpy as np
import warnings

from nilearn import plotting, datasets
import nibabel as nb

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

import definitions.layout_styles as styles

# ===== DATA PROCESSING FUNCTIONS ==============================================================

# results_directory = './assets/results/'
# /Users/Serena/Desktop/PA-brain-project/results/
# def check_results_directory(input_path):


def detect_models(resdir):
    # Make sure path is correctly specified
    resdir = f'{resdir}/' if resdir[-1] != '/' else resdir

    # List all results; ASSUME all results are stored in one directory
    all_results = [x[0].split('/')[-1] for x in os.walk(resdir)][1:]

    # Clean bad result files, and notify user ========================================================
    # ASSUME that if the stack_names files exists the folder is good
    # ASSUME directory names with structure = lh.name.measure
    for result in all_results:
        if not os.path.isfile(f'{resdir}{result}/stack_names.txt'):
            print(f'There is a problem with "{result}". Removing the model from overview')
            all_results.remove(result)

    results_df = pd.DataFrame([x.split('.') for x in all_results], columns=['hemi','name','measure'])
    count_hemis = results_df.groupby(['name', 'measure']).count()
    only_one_hm = list(count_hemis.loc[count_hemis.hemi < 2].index)
    if len(only_one_hm) > 0:
        to_remove = [f'{mod}.{meas}' for mod, meas in only_one_hm]
        print(f'Models: {to_remove} where estimated in one hemisphere only. This is currently not supported')
        clean_results = [x for x in all_results if not any(bad_model in x for bad_model in to_remove)]
    else:
        clean_results = all_results

    # Extract the terms for each model ===============================================================
    # ASSUME that if the model_name is the same, then lh/rh have the same model
    out_terms = {}
    for result in clean_results:
        model_name = '.'.join(result.split('.')[1:3])
        if not model_name in list(out_terms.keys()):
            # Read terms (i.e. stack) names
            stacks = pd.read_table(f'{resdir}{result}/stack_names.txt', delimiter="\t")

            out_terms[model_name] = dict(zip(list(stacks.stack_name)[1:], list(stacks.stack_number)[1:]))

    return out_terms


def extract_results(resdir, model, term, thr='30'):

    stack = detect_models(resdir)[model][term]

    min_beta = []
    max_beta = []
    med_beta = []
    n_clusters = []

    sign_clusters_left_right = {}
    sign_betas_left_right = {}

    for hemi in ['left', 'right']:
        mdir = f'{resdir}{hemi[0]}h.{model}'
        # Read significant cluster map
        ocn = nb.load(f'{mdir}/stack{stack}.cache.th{thr}.abs.sig.ocn.mgh')
        sign_clusters = np.array(ocn.dataobj).flatten()

        if not np.any(sign_clusters):  # all zeros = no significant clusters
            betas = np.empty(sign_clusters.shape)
            betas.fill(np.nan)
            n_clusters.append(0)
        else:
            # Read beta map
            coef = nb.load(f'{mdir}/stack{stack}.coef.mgh')
            betas = np.array(coef.dataobj).flatten()

            # Set non-significant betas to NA
            mask = np.where(sign_clusters == 0)[0]
            betas[mask] = np.nan

            n_clusters.append(np.max(sign_clusters))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            min_beta.append(np.nanmin(betas))
            max_beta.append(np.nanmax(betas))
            med_beta.append(np.nanmean(betas))

        sign_clusters_left_right[hemi] = sign_clusters
        sign_betas_left_right[hemi] = betas

    return np.nanmin(min_beta), np.nanmax(max_beta), np.nanmean(med_beta), n_clusters, sign_clusters_left_right, sign_betas_left_right


def compute_overlap(resdir, model1, term1, model2, term2):

    sign_clusters1 = extract_results(resdir, model1, term1)[4]
    sign_clusters2 = extract_results(resdir, model2, term2)[4]

    ovlp_maps = {}
    ovlp_info = {}

    for hemi in ['left', 'right']:
        sign1, sign2 = sign_clusters1[hemi], sign_clusters2[hemi]

        sign1[sign1 > 0] = 1
        sign2[sign2 > 0] = 2

        # Create maps
        ovlp_maps[hemi] = np.sum([sign1, sign2], axis=0)

        # Extract info
        uniques, counts = np.unique(ovlp_maps[hemi], return_counts=True)
        ovlp_info[hemi] = dict(zip(uniques, counts))
        ovlp_info[hemi].pop(0)  # only significant clusters

    # Merge left and right info
    info = {k: [ovlp_info['left'].get(k, 0) + ovlp_info['right'].get(k, 0)] for k in
            set(ovlp_info['left']) | set(ovlp_info['right'])}
    percent = [round(i[0] / sum(sum(info.values(), [])) * 100, 1) for i in info.values()]

    for i, k in enumerate(info.keys()):
        info[k].append(percent[i])

    return info, ovlp_maps


# ===== PLOTTING FUNCTIONS ===================================================================

def fetch_surface(resolution):
    # Size / number of nodes per map
    n_nodes = {'fsaverage': 163842,
               'fsaverage6': 40962,
               'fsaverage5': 10242}

    return datasets.fetch_surf_fsaverage(mesh=resolution), n_nodes[resolution]

# ---------------------------------------------------------------------------------------------


def plot_surfmap(resdir,
                 model,
                 term,
                 surf='pial',  # 'pial', 'infl', 'flat', 'sphere'
                 resol='fsaverage6',
                 output='betas'):

    min_beta, max_beta, mean_beta, n_clusters, sign_clusters, sign_betas = extract_results(resdir, model, term)

    fs_avg, n_nodes = fetch_surface(resol)

    brain3D = {}

    for hemi in ['left', 'right']:

        if output == 'clusters':
            stats_map = sign_clusters[hemi]

            max_val = int(np.nanmax(n_clusters))
            min_val = thresh = 1

            cmap = plt.get_cmap(styles.CLUSTER_COLORMAP, max_val)

        else:
            stats_map = sign_betas[hemi]

            max_val = max_beta
            min_val = min_beta

            if max_val < 0 and min_val < 0:  # all negative associations
                thresh = max_val
            elif max_val > 0 and min_val > 0:  # all positive associations
                thresh = min_val
            else:
                thresh = np.nanmin(abs(stats_map))

            cmap = styles.BETA_COLORMAP

        brain3D[hemi] = plotting.plot_surf(
                surf_mesh=fs_avg[f'{surf}_{hemi}'],  # Surface mesh geometry
                surf_map=stats_map[:n_nodes],  # Statistical map
                bg_map=fs_avg[f'sulc_{hemi}'],  # alpha=.2, only in matplotlib
                darkness=0.7,
                hemi=hemi,
                view='lateral',
                engine='plotly',  # axes=axs[0] # only for matplotlib
                cmap=cmap,
                symmetric_cmap=False,
                colorbar=True,
                vmin=min_val, vmax=max_val,
                cbar_vmin=min_val, cbar_vmax=max_val,
                avg_method='median',
                # title=f'{hemi} hemisphere',
                # title_font_size=20,
                threshold=thresh
            ).figure

    return brain3D

# ---------------------------------------------------------------------------------------------


def plot_overlap(resdir, model1, term1, model2, term2, surf='pial', resol='fsaverage6'):

    ovlp_maps = compute_overlap(resdir, model1, term1, model2, term2)[1]

    fs_avg, n_nodes = fetch_surface(resol)

    cmap = ListedColormap([styles.OVLP_COLOR1, styles.OVLP_COLOR2, styles.OVLP_COLOR3])

    brain3D = {}

    for hemi in ['left', 'right']:

        brain3D[hemi] = plotting.plot_surf(
            surf_mesh=fs_avg[f'{surf}_{hemi}'],  # Surface mesh geometry
            surf_map=ovlp_maps[hemi][:n_nodes],  # Statistical map
            bg_map=fs_avg[f'sulc_{hemi}'],  # alpha=.2, only in matplotlib
            darkness=0.7,
            hemi=hemi,
            view='lateral',
            engine='plotly',  # or matplolib # axes=axs[0] # only for matplotlib
            cmap=cmap,
            colorbar=False,
            vmin=1, vmax=3,
            threshold=1
        ).figure

    return brain3D
