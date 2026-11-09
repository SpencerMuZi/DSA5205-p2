# Video walkthrough script

Disclosed synthetic-narration draft using actual recorded command outputs and results. Team identity fields remain blank.

## 01. Regularized SPY market timing

This walkthrough presents a historical research project on daily SPY market timing. It covers the economic hypothesis, data construction, time alignment, training, validation, executable positions, and final out of sample results after trading costs. The narration is synthetic, and the charts and command outputs come from an executed research pipeline. It does not represent a presentation by named team members. The central finding is modest: the selected Ridge model reduces some realized risk but does not beat buy and hold on net compound growth or net Sharpe. That negative result is retained. The purpose is to demonstrate a complete and auditable research process, rather than to manufacture a successful trading strategy.

## 02. Economic story and competing mechanisms

The economic hypothesis begins with two competing mechanisms. Recent returns might continue when information is incorporated gradually or investors adjust positions slowly. Short moves might instead reverse after temporary liquidity pressure. Recent volatility can describe a different market state, changing the reliability of either pattern. We therefore combine several return lookbacks, a moving average gap, and realized volatility. A regularized linear model estimates their joint relationship with the next executable return. This is deliberately a small model. It does not assume that a nonlinear model, a large feature set, or an elaborate neural network must help. The economic mechanisms motivate the experiment, but the backtest cannot identify them causally.

## 03. Actual data-build command

The repository provides separate commands for data, validation, testing, figures, and the report. This screen shows actual captured output from the data command. The original run downloaded SPY daily prices and corporate actions from Yahoo Finance using yfinance. The demonstrated rerun uses that frozen local cache, so it is explicitly labeled cache rather than pretending to perform a new download. Prices are requested from January twenty ten through December twenty twenty five. The download uses unadjusted OHLC, a separate adjusted close, and dividend and split events. A provenance file records the source options and the SHA two fifty six digest of the serialized input used by every following stage.

## 04. Data integrity before modeling

Data quality is checked before any model is fitted. All four thousand and twenty four observed sessions match the expected exchange calendar, including special closures. There are no duplicate session dates, missing fields, or zero volume observations. The code checks positive finite prices, nonnegative distributions, and valid high and low ordering. It does not interpolate market prices or fill weekends. Sixty four dividend events and no split events are observed. Extreme market returns are retained rather than removed after inspecting the full sample. A five calendar day gap in twenty twelve is consistent with the exchange schedule. The code would fail explicitly on a calendar mismatch or an unsupported split.

## 05. Five features known at the close

The five features are the one session return, five session return, twenty session return, the adjusted close divided by its twenty session average minus one, and the standard deviation of the latest twenty adjusted returns. Every input is available after the signal session closes. The first twenty rows are warm up observations, not trading opportunities with invented history. Scaling is fitted only on the current training window and then applied forward with the fitted model. Absolute backward adjusted price levels are never predictors. A common later adjustment factor cancels from these ratios and return statistics. A unit test verifies this property, although arbitrary future vendor corrections can still change a downloaded history.

## 06. A forecast must match an executable return

A critical design choice is matching the prediction label to a return the strategy could actually earn. The signal is calculated after the close of session t. Trading takes place at the next session's open, and the holding interval ends at the following open. The label is therefore an open to open return, not a close to close return. Training samples are included only when their exit date is already known by the current decision close. This excludes the most recent immature labels even if their feature rows already exist. The maturity filter is checked in the model audit and tested by perturbing future prices and confirming that past predictions remain unchanged.

## 07. Dividend entitlement is explicit

Dividend accounting requires care because adjusted prices and explicit cash flows should not be mixed inconsistently. Execution uses raw opening prices. A position bought on an ex dividend date does not receive that day's dividend. A position carried from the previous session into the exit ex dividend date does receive it. The holding return therefore adds the exit date distribution to the exit opening price before dividing by the entry opening price. This research convention credits the dividend receivable at the ex date opening, abstracting from the actual payment date. Feature returns use vendor adjusted close, but execution profits use explicit distributions. The report documents the small difference between vendor adjustment and explicit cash return conventions.

## 08. Frozen chronological design

The chronological split separates development, selection, and final evaluation. The initial development history runs from twenty ten through twenty eighteen. The forward validation period is twenty nineteen through twenty twenty one. The final holdout is twenty twenty two through twenty twenty five. At each new decision month, the model is refitted on the latest twelve hundred and sixty realized training outcomes. It requires at least one thousand observations. The first test signal is formed at the end of twenty twenty one for entry at the first opening session of twenty twenty two. Earlier test outcomes may later enter training after they occur, but alpha, the features, the window, and the trading rule remain fixed.

## 09. Ridge and overfitting control

Ridge regression minimizes squared return errors plus alpha times the sum of squared coefficients. The intercept is not penalized. Standardization makes the penalty comparable across differently scaled features. The implementation uses the deterministic singular value decomposition solver through a scikit learn pipeline. The only selected hyperparameter is alpha, with four values fixed before the initial download: zero point one, one, ten, and one hundred. There is no search over dozens of indicators, alternative thresholds, or model families. Restricting that search is an important overfitting control. Regularization can reduce estimation instability, but it cannot guarantee that noisy market features contain a useful predictive signal.

## 10. Actual validation output and selection

This screen shows actual validation command output for all four candidates. Each model is fitted forward through time, converted into positions, and assessed after five basis point costs. The declared criterion is highest validation net Sharpe, and ties within numerical tolerance choose the larger penalty. Alpha zero point one and alpha one produce the same validation trading outcomes because their prediction signs coincide. Alpha one is therefore selected. The selection file records protocol, input, and validation table hashes before final testing. Only the selected alpha is evaluated on the holdout. The validation Sharpe is above one point two, but this attractive selected result is not treated as a forecast of future performance.

## 11. From forecasts to positions and fees

The position map is intentionally simple. A strictly positive predicted return produces a full SPY position; otherwise the strategy holds cash. There is no leverage or short selling. Cash interest is zero by assumption. Every change between cash and SPY creates one unit of one way turnover. The cost is a five basis point fraction of pretrade equity and is deducted before that interval's asset return. Initial entry and final liquidation are included. Buy and hold pays one initial purchase charge and one final sale charge. The moving average baseline uses identical timing and fees. Costs are multiplicative, so the code does not accidentally charge a sale after the relevant interval has already earned returns.

## 12. Actual final holdout output

The final test uses the selected model and contains one thousand and two holding intervals. This is actual command output rather than a hand entered performance table. After five basis point single side costs, Ridge compound annual growth is 6.54 percent, annualized volatility is 15.72 percent, and Sharpe is 0.481. Buy and hold compound growth is 11.18 percent with Sharpe 0.670. The moving average baseline grows at 3.69 percent. We retain these results even though the model does not win. There is no second holdout pass used to choose a more flattering model or a different set of features.

## 13. Cumulative wealth: growth sacrificed

The cumulative wealth plot shows the economic result over the full holdout, including all fees. One initial dollar becomes approximately 1.286 dollars under Ridge and 1.524 dollars under buy and hold. The timing strategy avoids some negative intervals but also misses gains. SPY's average return is positive during this period, so moving into cash has an opportunity cost. The binary position rule also discards forecast magnitude. A tiny positive forecast receives the same full investment as a large positive forecast. Small forecast changes near zero can therefore trigger trades whose costs are substantial relative to the expected signal. This helps explain why prediction and trading value must be evaluated separately.

## 14. Drawdown: a trade-off, not a victory

The drawdown plot provides a risk perspective. Ridge has a smaller full period maximum drawdown than buy and hold, but still experiences a substantial loss from a prior peak. Its lower realized volatility is partly consistent with holding less equity. The moving average rule has lower volatility still, together with lower compound growth. Drawdown is path dependent: a smaller observed drawdown is not a guarantee about the next crisis and not proof of crash prediction. The accounting includes initial wealth in the running peak, so an immediate loss is counted correctly. The report therefore describes a risk and growth trade off, rather than presenting the lower drawdown as sufficient evidence of a superior strategy.

## 15. Annual results reveal instability

The year by year breakdown shows where the aggregate result comes from. Ridge loses less than buy and hold during twenty twenty two, but trails buy and hold in each of the following three years. The benefit in the down year does not compensate for the missed gains and trading costs across the complete holdout. Annual results use a continuous portfolio path. There is no artificial liquidation and repurchase each December, and costs remain assigned to the intervals when they occur. Short annual Sharpe estimates are noisy. The year table is descriptive; it is not a license to choose the winner for each year after seeing what happened.

## 16. Costs explain much of the gap

The sensitivity plot changes only the cost assumption, holding predictions and positions fixed. Ridge generates two hundred and forty six units of total one way turnover, compared with two for buy and hold. At zero cost, its Sharpe is approximately zero point six seven eight, close to buy and hold's zero point six seven two. Five basis point costs lower Ridge Sharpe to about zero point four eight one. At ten basis points it falls further. These are scenarios rather than empirical measurements of auction costs. The main assumption was chosen in advance. The result illustrates why a seemingly competitive gross strategy can fail once realistic implementation frictions are even approximately represented.

## 17. Prediction quality and exposure

Prediction error is compared with a historical mean estimated from the same mature rolling training window. Out of sample R squared is negative, so Ridge does not beat that simple forecast on squared error. Directional accuracy is close to fifty one percent, but accuracy ignores return magnitude and costs. Ridge is invested for about sixty nine percent of holding intervals, which helps explain lower volatility. The report includes an ex post constant exposure diagnostic to illustrate that point. Because its exposure is calculated from the holdout, it is clearly labeled a diagnostic, not an investable benchmark. Neither reduced exposure nor a slightly better hit rate establishes economically valuable timing skill.

## 18. Actual integrity-test output

This screen shows actual test output from the repository. The tests use synthetic fixtures only to verify code behavior; reported strategy returns always use downloaded market observations. Tests perturb future prices and confirm that earlier features, fitted scaling, and predictions remain unchanged. Other tests check label maturity, dividend entitlement, monthly refitting, initial and final transaction fees, all cash positions, calendar boundaries, and drawdown from starting capital. Synthetic data are never substituted when a download fails. A separate clean environment check installs the declared dependencies and reruns the frozen analysis on the same local input snapshot. Reproduction is conditional on matching that snapshot because vendor histories can be revised.

## 19. Reproduce and inspect the artifacts

The repository contains exact setup and run commands, pinned package versions, the frozen configuration, input provenance, the validation selection file, model fit audits, predictions, and portfolio accounting tables. Figures and the 18 page LaTeX report are generated from those saved results. The walkthrough log records the original research commands actually executed and their exit codes. The paper rewrite has a separate compilation manifest. Team names and contributions are intentionally blank until the user supplies them; no participation is invented. The raw vendor price cache is excluded from Git, so a clean checkout downloads its own copy or uses an authorized matching local snapshot. If upstream data change, the stored lock refuses to overwrite the original experiment silently. A revised input requires a separately disclosed run.

## 20. Conclusion and honest next steps

The final conclusion is that this small Ridge timing design does not establish net superiority over buy and hold. It has lower realized exposure and some reduction in drawdown, but lower net growth and Sharpe under the declared cost assumption. Prediction R squared is negative, and turnover is a major source of drag. The useful output is a complete, transparent experiment with explicit timing and honest interpretation. Future work could examine a no trade region, smoother position sizes, or a pre specified risk matched benchmark, but those ideas have not been optimized on this holdout. Before submission, the team should review the code and report, fill its identity and contribution fields, and decide how to present these findings in its own reviewed video.
