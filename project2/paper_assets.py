"""Legacy v1.1 asset generator; the authoritative Group 33 sources are compiled as supplied."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from .core import FEATURES, digest, write_json

DEST = Path("paper/generated")
COLORS = {"Ridge": "#087f8c", "MA20": "#cf8a24", "Buy-and-hold": "#263b5e"}


def tex(value):
    return str(value).replace("\\", r"\textbackslash{}").replace("_", r"\_").replace("%", r"\%").replace("&", r"\&").replace("#", r"\#")


def table(name, headers, rows, alignment=None):
    alignment = alignment or "l" + "r" * (len(headers) - 1)
    lines = [r"\begin{tabular}{" + alignment + "}", r"\toprule",
             " & ".join(headers) + r" \\", r"\midrule"]
    lines.extend(" & ".join(map(str, row)) + r" \\" for row in rows)
    lines += [r"\bottomrule", r"\end{tabular}"]
    (DEST / f"{name}.tex").write_text("\n".join(lines) + "\n")


def build():
    if Path('paper/metadata.tex').exists():
        raise RuntimeError('Group 33 uses supplied Overleaf sources. Run python -m project2.report to compile them without overwriting their tables, figures, or metadata.')
    DEST.mkdir(parents=True, exist_ok=True)
    config = json.loads(Path('config.json').read_text())
    author_line = r'\normalsize DSA5205 Project 2\quad\textbar\quad November 2026'
    if config.get('team_members'):
        author_line = (r'\normalsize ' + ', '.join(tex(n) for n in config['team_members'])
                       + r'\\[-2pt]\small ' + tex(config.get('team_name',''))
                       + r'\\[-2pt]\small DSA5205 Project 2\quad\textbar\quad November 2026')
    (DEST/'authors.tex').write_text(r'\newcommand{\PaperAuthors}{'+author_line+'}\n')
    identity = [r"\begin{tabularx}{\textwidth}{@{}p{.26\textwidth}X@{}}", r"\toprule",
                "Group / team name & " + tex(config.get('team_name','')) + r" \\",
                "Full member roster & " + tex(', '.join(config.get('team_members',[]))) + r" \\",
                r"\midrule", r"Member & Contribution \\", r"\midrule"]
    contributions = config.get('contributions',{})
    identity.extend(tex(member) + ' & ' + tex(contribution) + r" \\" for member,contribution in contributions.items())
    if not contributions:
        identity.extend([r"\rule{0pt}{18pt} & \\" for _ in range(4)])
    identity.extend([r"\bottomrule",r"\end{tabularx}"])
    (DEST/'team.tex').write_text('\n'.join(identity)+'\n')
    metrics = pd.read_csv("output/tables/test_metrics.csv").set_index("strategy")
    grid = pd.read_csv("output/tables/validation_grid.csv")
    annual = pd.read_csv("output/tables/annual_metrics.csv")
    costs = pd.read_csv("output/tables/cost_sensitivity.csv")
    pred = pd.read_csv("output/tables/test_predictions.csv", parse_dates=["decision_date", "entry_date", "exit_date"])
    fits = pd.read_csv("output/tables/test_fit_audit.csv")
    events = pd.read_csv("output/tables/dividend_event_checks.csv")
    pm = json.loads(Path("output/prediction_metrics.json").read_text())
    audit = json.loads(Path("output/data_audit.json").read_text())
    diag = json.loads(Path("output/exposure_diagnostic.json").read_text())
    paths = {name: pd.read_csv(f"output/tables/test_path_{key}.csv", parse_dates=["exit_date", "entry_date"])
             for name, key in [("Ridge", "ridge"), ("MA20", "ma20"), ("Buy-and-hold", "buy_hold")]}
    names = ["Ridge timing", "MA20 timing", "SPY buy-and-hold"]
    fmtp = lambda x: f"{100 * float(x):.2f}"
    macro = {"RidgeCAGR": fmtp(metrics.loc[names[0], "cagr"])+r"\%",
             "BHCAGR": fmtp(metrics.loc[names[2], "cagr"])+r"\%",
             "RidgeSharpe": f"{metrics.loc[names[0], 'sharpe_rf_zero']:.3f}",
             "BHSharpe": f"{metrics.loc[names[2], 'sharpe_rf_zero']:.3f}",
             "RidgeMDD": fmtp(metrics.loc[names[0], 'max_drawdown'])+r"\%",
             "BHMDD": fmtp(metrics.loc[names[2], 'max_drawdown'])+r"\%",
             "RidgeExposure": fmtp(metrics.loc[names[0], 'exposure'])+r"\%",
             "OOSRsquared": f"{pm['oos_r2_vs_past_mean']:.5f}",
             "HitRate": fmtp(pm['directional_accuracy'])+r"\%",
             "OutcomeCount": f"{len(pred):,}", "SessionCount": f"{audit['raw_rows']:,}",
             "FitCount": str(len(fits)), "TurnoverCount": f"{metrics.loc[names[0], 'total_turnover']:.0f}"}
    (DEST / "numbers.tex").write_text("% Generated from frozen CSV/JSON artifacts.\n" + "\n".join("\\newcommand{\\"+k+"}{"+v+"}" for k,v in macro.items()) + "\n")
    rows=[]
    for label,col,kind in [("CAGR (\\%)","cagr","p"),("Arithmetic return (\\%)","annualized_arithmetic_return","p"),
                           ("Volatility (\\%)","annualized_volatility","p"),("Sharpe ($r_f=0$)","sharpe_rf_zero","s"),
                           ("Max. drawdown (\\%)","max_drawdown","p"),("Total return (\\%)","total_return","p"),
                           ("Equity exposure (\\%)","exposure","p"),("One-way turnover","total_turnover","k")]:
        row=[label]
        for name in names:
            x=metrics.loc[name,col]
            row.append(fmtp(x) if kind=="p" else (f"{x:.3f}" if kind=="s" else f"{x:.0f}"))
        rows.append(row)
    table("headline", ["Metric", "Ridge", "MA20", "Buy-and-hold"], rows)
    table("validation", [r"$\alpha$", r"CAGR (\%)", "Net Sharpe", r"Exposure (\%)"],
          [[f"{r.alpha:g}",fmtp(r.cagr),f"{r.sharpe_rf_zero:.4f}",fmtp(r.exposure)] for _,r in grid.iterrows()])
    table("validation_full", [r"$\alpha$",r"CAGR (\%)","Sharpe",r"Vol. (\%)",r"MDD (\%)","Turnover",r"$R^2_{\mathrm{OOS}}$"],
          [[f"{r.alpha:g}",fmtp(r.cagr),f"{r.sharpe_rf_zero:.4f}",fmtp(r.annualized_volatility),fmtp(r.max_drawdown),f"{r.total_turnover:.0f}",f"{r.oos_r2_vs_past_mean:.5f}"] for _,r in grid.iterrows()])
    table("costs", ["bps",r"Ridge CAGR (\%)","Sharpe",r"BH CAGR (\%)","BH Sharpe"],
          [[f"{c:g}",fmtp(costs[(costs.cost_bps==c)&(costs.strategy==names[0])].iloc[0].cagr),
            f"{costs[(costs.cost_bps==c)&(costs.strategy==names[0])].iloc[0].sharpe_rf_zero:.3f}",
            fmtp(costs[(costs.cost_bps==c)&(costs.strategy==names[2])].iloc[0].cagr),
            f"{costs[(costs.cost_bps==c)&(costs.strategy==names[2])].iloc[0].sharpe_rf_zero:.3f}"] for c in [0.,5.,10.]])
    table("costs_full", ["Strategy","bps",r"CAGR (\%)","Sharpe",r"MDD (\%)","Final wealth"],
          [[{"Ridge timing":"Ridge","MA20 timing":"MA20","SPY buy-and-hold":"Buy-and-hold"}[r.strategy],
            f"{r.cost_bps:g}",fmtp(r.cagr),f"{r.sharpe_rf_zero:.3f}",fmtp(r.max_drawdown),f"{1+r.total_return:.4f}"] for _,r in costs.iterrows()], "llrrrr")
    table("annual", ["Year",r"Ridge (\%)",r"MA20 (\%)",r"Buy-and-hold (\%)"],
          [[str(y)]+[fmtp(annual[(annual.year==y)&(annual.strategy==n)].iloc[0].total_return) for n in names] for y in sorted(annual.year.unique())])
    table("annual_full", ["Strategy","Year",r"Return (\%)",r"Vol. (\%)","Sharpe",r"Exposure (\%)","Turnover"],
          [[{"Ridge timing":"Ridge","MA20 timing":"MA20","SPY buy-and-hold":"Buy-and-hold"}[r.strategy],str(r.year),
            fmtp(r.total_return),fmtp(r.annualized_volatility),f"{r.sharpe_rf_zero:.3f}",fmtp(r.exposure),f"{r.turnover:.0f}"] for _,r in annual.iterrows()], "llrrrrr")
    positive = pred.target > 0
    table("confusion", ["Forecast position", "$y>0$", r"$y\leq 0$", "Total"],
          [["SPY",int(((pred.ridge_weight==1)&positive).sum()),int(((pred.ridge_weight==1)&~positive).sum()),int(pred.ridge_weight.sum())],
           ["Cash",int(((pred.ridge_weight==0)&positive).sum()),int(((pred.ridge_weight==0)&~positive).sum()),int((pred.ridge_weight==0).sum())]])
    dist=[]
    for name,col in [("Model forecast","prediction"),("Realized holding return","target"),("Historical-mean forecast","historical_mean")]:
        x=pred[col]*10000
        dist.append([name,f"{x.mean():.3f}",f"{x.std(ddof=1):.3f}",f"{x.min():.3f}",f"{x.quantile(.5):.3f}",f"{x.max():.3f}"])
    table("prediction_distribution", ["Series (bps)","Mean","SD","Min.","Median","Max."], dist)
    conditional=[]
    for label,part in [("Invested intervals",pred[pred.ridge_weight==1]),("Cash intervals",pred[pred.ridge_weight==0])]:
        conditional.append([label,len(part),f"{part.target.mean()*10000:.3f}",f"{part.target.std(ddof=1)*10000:.3f}",fmtp((part.target>0).mean())])
    table("conditional_returns", ["Ridge decision","Count","Mean $y$ (bps)","SD (bps)",r"Positive (\%)"],conditional)
    table("audit_fits", ["Fit date","First training signal","Last training signal","Latest label exit","$N$"],
          [[r.fit_date,r.train_first_decision,r.train_last_decision,r.max_label_exit,str(r.n_train)] for _,r in fits.iterrows()], "llllr")
    table("scaler", ["Feature","First mean","First scale","Last mean","Last scale"],
          [[r"\texttt{"+tex(f)+"}"]+[f"{r[f'{prefix}_{f}']:.6f}" for r,prefix in [(fits.iloc[0],"mean"),(fits.iloc[0],"scale"),(fits.iloc[-1],"mean"),(fits.iloc[-1],"scale")]] for f in FEATURES])
    table("coef_summary", ["Feature","Mean (bps)","Min. (bps)","Max. (bps)","Sign changes"],
          [[r"\texttt{"+tex(f)+"}",f"{fits['coef_'+f].mean()*10000:.3f}",f"{fits['coef_'+f].min()*10000:.3f}",f"{fits['coef_'+f].max()*10000:.3f}",str(int((np.sign(fits['coef_'+f]).diff().dropna()!=0).sum()))] for f in FEATURES])
    table("event_checks", ["Ex-date","Dividend (USD)",r"Vendor return (\%)",r"Cash return (\%)",r"$\Delta$ (bps)"],
          [[r.ex_date,f"{r.Dividends:.4f}",f"{r.vendor_close_return*100:.5f}",f"{r.explicit_close_total_return*100:.5f}",f"{r.return_difference*10000:.5f}"] for _,r in events.iloc[[0,1,-2,-1]].iterrows()])
    # Exact log-wealth drag for binary weights: K identical single-side factors.
    drag=[]
    for n in names:
        m=metrics.loc[n]; k=int(m.total_turnover); factor=(1-.0005)**k
        gross=costs[(costs.cost_bps==0)&(costs.strategy==n)].iloc[0]
        assert np.isclose((1+m.total_return)/(1+gross.total_return),factor,rtol=1e-12)
        drag.append([{"Ridge timing":"Ridge","MA20 timing":"MA20","SPY buy-and-hold":"Buy-and-hold"}[n],str(k),f"{factor:.6f}",f"{-252/len(pred)*k*np.log1p(-.0005)*100:.3f}"])
    table("log_drag", ["Strategy","$K$","Net/gross wealth",r"Annual log drag (\%)"], drag)
    decisions = pred[["decision_date","entry_date","exit_date","prediction","target","ridge_weight"]].head(6)
    table("trace", ["Decision","Entry","Exit","Forecast (bps)","Realized (bps)","$w$"],
          [[str(r.decision_date.date()),str(r.entry_date.date()),str(r.exit_date.date()),f"{r.prediction*10000:.3f}",f"{r.target*10000:.3f}",f"{r.ridge_weight:.0f}"] for _,r in decisions.iterrows()], "lllrrr")
    summary={"positive_return_fraction":float(positive.mean()),
             "forecasts_within_5bps_fraction":float((pred.prediction.abs()<.0005).mean()),
             "mean_abs_forecast_bps":float(pred.prediction.abs().mean()*10000),
             "prediction_target_correlation":float(pred.prediction.corr(pred.target)),
             "conditional_invested_return_bps":float(pred[pred.ridge_weight==1].target.mean()*10000),
             "conditional_cash_return_bps":float(pred[pred.ridge_weight==0].target.mean()*10000),
             "note":"Descriptive analysis of frozen predictions only; no refitting, selection, or alternative strategy testing."}
    write_json(DEST/"descriptive_diagnostics.json",summary)
    # Compact vector graphics sized for their final physical width in a two-column paper.
    plt.rcParams.update({"font.family":"serif","font.serif":["STIXGeneral"],"mathtext.fontset":"stix",
                         "font.size":8.5,"axes.labelsize":8.5,"axes.titlesize":9,"legend.fontsize":8,
                         "axes.spines.top":False,"axes.spines.right":False,"axes.grid":True,"grid.alpha":.16,
                         "pdf.fonttype":42,"savefig.facecolor":"white","lines.linewidth":1.25})
    def save(fig,name):
        fig.tight_layout(pad=.35)
        fig.savefig(DEST/f"{name}.pdf",bbox_inches="tight",pad_inches=.03)
        fig.savefig(DEST/f"{name}.png",dpi=180,bbox_inches="tight",pad_inches=.03)
        plt.close(fig)
    for kind in ["wealth","drawdown"]:
        fig,ax=plt.subplots(figsize=(6.8,2.35))
        for name,path in paths.items():
            if kind=="wealth":
                x=pd.concat([path.entry_date.iloc[:1],path.exit_date],ignore_index=True); y=np.r_[1,path.wealth]
            else:
                x=path.exit_date; y=100*(path.wealth/np.maximum.accumulate(np.r_[1.,path.wealth])[1:]-1)
            ax.plot(x,y,label=name,color=COLORS[name])
        ax.set(xlabel="Holding-interval exit date",ylabel="Wealth ($1 initially)" if kind=="wealth" else "Drawdown (%)")
        ax.legend(frameon=False,ncol=3,loc="upper left" if kind=="wealth" else "lower right")
        ax.xaxis.set_major_locator(mdates.YearLocator());ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        save(fig,kind)
    fig,ax=plt.subplots(figsize=(3.3,2.25))
    for name,long in zip(COLORS,names):
        part=costs[costs.strategy==long]
        ax.plot(part.cost_bps,part.sharpe_rf_zero,"o-",ms=3,label=name,color=COLORS[name])
    ax.set(xlabel="Single-side cost (bps)",ylabel="Annualized Sharpe",xticks=[0,5,10]);ax.legend(frameon=False,loc="lower left")
    save(fig,"cost_sharpe")
    fig,ax=plt.subplots(figsize=(3.3,2.25))
    ax.plot(grid.alpha,grid.sharpe_rf_zero,"o-",ms=4,color=COLORS["Ridge"])
    ax.set(xscale="log",xlabel=r"Ridge penalty $\alpha$",ylabel="Validation net Sharpe")
    for _,r in grid.iterrows():ax.annotate(f"{r.sharpe_rf_zero:.3f}",(r.alpha,r.sharpe_rf_zero),xytext=(0,8),textcoords="offset points",ha="center",fontsize=7.5)
    ax.margins(y=.25);save(fig,"validation")
    fig,axs=plt.subplots(1,2,figsize=(6.8,2.5))
    for ax,col in zip(axs,["total_return","sharpe_rf_zero"]):
        pivot=annual.pivot(index="year",columns="strategy",values=col)[names]
        if col=="total_return":pivot*=100
        pivot.plot.bar(ax=ax,rot=0,color=list(COLORS.values()),width=.78,legend=False)
        ax.set(xlabel="Exit year",ylabel="Net return (%)" if col=="total_return" else "Sharpe ($r_f=0$)")
        ax.axhline(0,c="#555",lw=.5)
    handles,_=axs[0].get_legend_handles_labels();axs[0].legend(handles,list(COLORS),frameon=False,fontsize=7)
    save(fig,"annual")
    fig,ax=plt.subplots(figsize=(6.8,2.2))
    for name in ["Ridge","MA20"]:
        p=paths[name].set_index("exit_date").weight.resample("ME").mean()
        ax.plot(p.index,100*p,label=name,color=COLORS[name])
    ax.set(xlabel="Month",ylabel="Average equity exposure (%)",ylim=(-3,103));ax.legend(frameon=False,ncol=2)
    save(fig,"exposure")
    fig,ax=plt.subplots(figsize=(6.8,2.7))
    for f in FEATURES:ax.plot(pd.to_datetime(fits.fit_date),10000*fits['coef_'+f],label=f.replace('_',' '))
    ax.axhline(0,c="#555",lw=.5);ax.set(xlabel="Monthly fit date",ylabel="Coefficient (bps per training SD)")
    ax.legend(frameon=False,ncol=3,fontsize=7);save(fig,"coefficients")
    fig,axs=plt.subplots(1,2,figsize=(6.8,2.5))
    axs[0].scatter(pred.prediction*100,pred.target*100,s=3,alpha=.35,c=COLORS["Ridge"],rasterized=True)
    axs[0].set(xlabel="Forecast (%)",ylabel="Realized holding return (%)")
    axs[0].axvline(0,c="#777",lw=.5);axs[0].axhline(0,c="#777",lw=.5)
    axs[1].hist(pred.prediction*10000,bins=35,color=COLORS["Ridge"],alpha=.9)
    axs[1].axvline(0,c="#263b5e",lw=.7);axs[1].set(xlabel="Forecast (bps)",ylabel="Count")
    save(fig,"predictions")
    fig,ax=plt.subplots(figsize=(6.8,1.75))
    spans=[("Development","2010-01-01","2018-12-31","#263b5e"),("Validation","2019-01-01","2021-12-31","#cf8a24"),("Final holdout","2022-01-01","2025-12-31","#087f8c")]
    for i,(name,a,b,c) in enumerate(spans):
        lo,hi=mdates.date2num(pd.Timestamp(a)),mdates.date2num(pd.Timestamp(b));ax.barh(i,hi-lo,left=lo,color=c,height=.55)
    ax.set_yticks(range(3),[s[0] for s in spans]);ax.invert_yaxis();ax.xaxis_date();ax.xaxis.set_major_locator(mdates.YearLocator(2));ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    save(fig,"timeline")
    sourcefiles=list(Path('output/tables').glob('*.csv'))+[Path(f'output/{n}.json') for n in ['selection','prediction_metrics','data_audit','run_manifest']]
    write_json(DEST/"sources.json",{str(p):digest(p) for p in sourcefiles})
    print(f"PAPER ASSETS: {len(list(DEST.glob('*.tex')))} tables/macros and {len(list(DEST.glob('*.pdf')))} vector figures")


if __name__=="__main__":
    build()
