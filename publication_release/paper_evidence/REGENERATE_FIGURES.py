from pathlib import Path
import csv, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
DATA=Path(__file__).resolve().parent
OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else DATA/'regenerated_figures'
OUT.mkdir(parents=True,exist_ok=True)
def read(p):return list(csv.DictReader(Path(p).open()))
NAMES={'pidd':'PIDD','sylhet':'Sylhet','brfss':'BRFSS','hospital130':'Hospital130'}
stress=read(DATA/'04_SUPPLEMENTARY_TABLES/frozen_availability_panel_degradation.csv')
plt.rcParams.update({'font.size':13,'axes.labelsize':13,'axes.titlesize':14,'legend.fontsize':13,'pdf.fonttype':42,'ps.fonttype':42})
colors={'pidd':'#0072B2','sylhet':'#D55E00','brfss':'#009E73','hospital130':'#555555'}
markers={'pidd':'o','sylhet':'s','brfss':'^','hospital130':'D'}
cal=read(DATA/'figure_data/panel_a_calibration.csv')
dec=read(DATA/'figure_data/panel_b_decision_curves.csv')
for mode,records,fn in [('cal',cal,'Figure_1_Calibration'),('dca',dec,'Figure_2_Decision_Curves')]:
    fig,axes=plt.subplots(2,2,figsize=(7.1,6.4))
    for ax,(ds,name) in zip(axes.flat,NAMES.items()):
        q=[r for r in records if r['dataset']==ds]
        if mode=='cal':
            ax.plot([0,1],[0,1],':',color='black',label='Ideal calibration')
            ax.plot([float(r['mean_predicted_probability']) for r in q],[float(r['observed_event_rate']) for r in q],marker=markers[ds],color=colors[ds],label='Accepted runtime policy')
            ax.set(xlim=(-.02,1.02),ylim=(-.02,1.02),xlabel='Mean predicted probability',ylabel='Observed event proportion')
        else:
            ax.plot([float(r['threshold']) for r in q],[float(r['model_net_benefit']) for r in q],color=colors[ds],label='Runtime policy')
            ax.plot([float(r['threshold']) for r in q],[float(r['treat_all_net_benefit']) for r in q],'--',color='black',label='Treat all')
            ax.axhline(0,color='black',linestyle=':',label='Treat none')
            ax.set(xlim=(.01,.5),xlabel='Threshold probability',ylabel='Net benefit per observation')
        ax.set_title(name)
        ax.grid(alpha=.2)
    handles=[Line2D([0],[0],color='black',linestyle=':',label='Ideal calibration'),Line2D([0],[0],color='black',marker='o',label='Accepted runtime policy')] if mode=='cal' else [Line2D([0],[0],color='black',label='Runtime policy'),Line2D([0],[0],color='black',linestyle='--',label='Treat all'),Line2D([0],[0],color='black',linestyle=':',label='Treat none')]
    fig.legend(handles=handles,loc='upper center',ncol=len(handles),frameon=False,fontsize=13)
    fig.tight_layout(rect=(0,0,1,.94),h_pad=1.4,w_pad=2.0)
    fig.savefig(OUT/(fn+'.pdf'));fig.savefig(OUT/(fn+'.png'),dpi=200);plt.close(fig)
fig,axes=plt.subplots(2,2,figsize=(7.1,5.3),layout='constrained')
for ax,(ds,name) in zip(axes.flat,NAMES.items()):
    q=[r for r in stress if r['dataset']==ds and r['system']=='availability_router']
    fullcount=max(float(r['available_feature_count']) for r in q)
    ax.axhline(0,ls=':',color='black')
    ax.scatter([100*float(r['available_feature_count'])/fullcount for r in q],[float(r['average_precision_degradation_from_full']) for r in q],color=colors[ds],marker=markers[ds],s=48,facecolors='none' if ds=='hospital130' else colors[ds])
    ax.set(title=name,xlabel='Full-schema predictors\nsupplied (%)',ylabel='Full minus panel AP',xlim=(0,105));ax.grid(alpha=.2)
fig.savefig(OUT/'Figure_3_Availability.pdf');fig.savefig(OUT/'Figure_3_Availability.png',dpi=200);plt.close(fig)

