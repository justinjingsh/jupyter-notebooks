# IG epics — common instruments

An **epic** is IG's identifier for one tradeable market, e.g. `IX.D.NASDAQ.IFA.IP`
("US Tech 100 Cash"). It is what you pass to `GET /prices/{epic}` and set as
`EPIC` in `download_ig_prices.ipynb`.

> **Epics are not a fixed public list.** The same underlying market has several
> epics (dated vs undated, CFD vs spread bet vs share dealing, full vs mini,
> different currencies), demo and live can differ, and IG occasionally re-issues
> them. Treat every epic below as a starting point and **confirm it with a market
> search** (see the end of this file) before relying on it.

## Confirmed in this workspace

These are used by the notebooks here or listed in the sibling
`ig-quant-trading` repo's `config.py` / `doc/glossary.md`:

| Epic | Instrument | Notes |
| --- | --- | --- |
| `IX.D.NASDAQ.IFA.IP` | US Tech 100 Cash (NASDAQ 100) | Default `EPIC` in `download_ig_prices.ipynb` |
| `IX.D.DAX.IFA.IP` | Germany 40 Cash (DAX) | |
| `IX.D.NIKKEI.IFA.IP` | Japan 225 Cash (Nikkei 225) | |
| `IX.D.ASX.IFT.IP` | Australia 200 Cash (ASX 200) | A$5 / point |
| `CS.D.EURUSD.CFD.IP` | Spot FX EUR/USD | |

## Commonly cited epics (verify before use)

### Stock indices — "Cash" / undated

| Epic | Instrument |
| --- | --- |
| `IX.D.NASDAQ.IFA.IP` | US Tech 100 (NASDAQ 100) |
| `IX.D.SPTRD.IFA.IP` | US 500 (S&P 500) |
| `IX.D.DOW.IFA.IP` | Wall Street (Dow Jones 30) |
| `IX.D.FTSE.IFA.IP` | FTSE 100 (UK 100) |
| `IX.D.DAX.IFA.IP` | Germany 40 (DAX) |
| `IX.D.CAC.IFA.IP` | France 40 (CAC 40) |
| `IX.D.IBEX.IFA.IP` | Spain 35 (IBEX 35) |
| `IX.D.STXE.IFA.IP` | EU Stocks 50 (Euro Stoxx 50) |
| `IX.D.NIKKEI.IFA.IP` | Japan 225 (Nikkei 225) |
| `IX.D.ASX.IFT.IP` | Australia 200 (ASX 200) |
| `IX.D.HANGSENG.IFA.IP` | Hong Kong HS50 (Hang Seng) |

Suffix commonly varies: `.IFA.` / `.IFE.` / `.IFS.` for the undated ("Cash")
bet, `.DAILY.` / `.IFD.` for the daily-funded variant, `.MONTH1.` etc. for dated
contracts.

### Forex — spot

| Epic | Pair |
| --- | --- |
| `CS.D.EURUSD.CFD.IP` | EUR/USD |
| `CS.D.GBPUSD.CFD.IP` | GBP/USD |
| `CS.D.USDJPY.CFD.IP` | USD/JPY |
| `CS.D.AUDUSD.CFD.IP` | AUD/USD |
| `CS.D.USDCAD.CFD.IP` | USD/CAD |
| `CS.D.USDCHF.CFD.IP` | USD/CHF |
| `CS.D.NZDUSD.CFD.IP` | NZD/USD |
| `CS.D.EURGBP.CFD.IP` | EUR/GBP |
| `CS.D.EURJPY.CFD.IP` | EUR/JPY |
| `CS.D.GBPJPY.CFD.IP` | GBP/JPY |

`.CFD.` is the standard-size CFD; `.MINI.` is the smaller contract; `.TODAY.` /
`.MONTH1.` are dated.

### Commodities

| Epic | Instrument |
| --- | --- |
| `CS.D.CFDGOLD.CFDGC.IP` | Spot Gold |
| `CS.D.CFDSILVER.CFM.IP` | Spot Silver |
| `CC.D.CL.USS.IP` | Oil — US Crude (WTI) |
| `CC.D.LCO.USS.IP` | Oil — Brent Crude |
| `CC.D.NG.USS.IP` | Natural Gas |
| `CS.D.COPPER.CFD.IP` | High Grade Copper |

### Crypto (region- and account-dependent; often unavailable)

| Epic | Instrument |
| --- | --- |
| `CS.D.BITCOIN.CFD.IP` | Bitcoin (BTC/USD) |
| `CS.D.ETHUSD.CFD.IP` | Ether (ETH/USD) |

### Shares

One epic per listing, prefixed `UA.D.` / `UB.D.` / `UC.D.` / `UD.D.` and usually
ending `.DAILY.IP` or `.CASH.IP`, e.g. Apple ≈ `UA.D.AAPL.DAILY.IP`. The exact
prefix per ticker is not predictable — always resolve shares via a market search.

## Epic structure, roughly

```
IX .  D  . NASDAQ  . IFA    . IP
│      │    │         │        └─ IG product marker (nearly always "IP")
│      │    │         └────────── contract variant: IFA/IFE/IFS = undated bet,
│      │    │                     DAILY/IFD = daily funded, MONTH1… = dated,
│      │    │                     CFD = standard CFD, MINI = mini, TODAY = dated FX
│      │    └──────────────────── market mnemonic (NASDAQ, DAX, EURUSD, CL, …)
│      └───────────────────────── nearly always "D"
└──────────────────────────────── asset class: IX = index, CS = FX + metals,
                                  CC = energies/softs, UA/UB/UC/UD = shares
```

## Discovering & confirming an epic

Use IG's free-text market search — `GET /markets?searchTerm=<term>` with
`Version: 1`. It returns `{ "markets": [ { epic, instrumentName, expiry, ... } ] }`.

Reusing `IGSession` from `download_ig_prices.ipynb`:

```python
ig = IGSession(API_KEY, USERNAME, PASSWORD, ACCOUNT_TYPE)

for m in ig._get("/markets", version="1", params={"searchTerm": "nasdaq"})["markets"]:
    print(m["epic"], "-", m["instrumentName"], f"({m.get('expiry')})")
```

The epics returned are the ones valid for **that** environment (demo vs live) and
account. `GET /markets/{epic}` (`Version: 3`) then gives full instrument detail
and a live bid/offer snapshot.
