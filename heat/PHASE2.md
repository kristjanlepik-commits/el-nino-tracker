# Heat Phase 2: city expansion

Phase 1 is 22 cities across five services, live. This maps what comes next,
what it costs, and what each city actually buys.

**Sources are VERIFIED, not assumed.** Every "viable" below means I have
fetched real data and confirmed the licence, the record length and that the
current summer is present. Everything untested says so.

## The bar, unchanged from Phase 1

1. Published source permitting **commercial reuse**
2. Record long enough for a rank to mean something, reaching **1971** for the
   percentile thresholds and **1991** for the sd baseline
3. **The current summer present**, not an archive ending last year
4. One station per city, nights and days from the same record
5. Station identity pinned by **ID, never by display name**

Point 3 is the one that kills candidates. Point 5 is the one that has bitten
three times: ECA&D's Murcia, GeoSphere's combined Vienna, Meteo-France's four
stations sharing the name NICE.

## VERIFIED VIABLE

### Prague, about a day

    source     CHMI, opendata.chmi.cz
    history    1921-2025, per-station JSON
    current    recent branch, through JULY 2026, TMI and TMA confirmed
    cut        07-31 rather than 08-03, since August is not yet published
    pattern    historical + recent, identical to DWD and Meteo-France

**Worth adding, and NOT evidence.** I proposed Prague and Warsaw as the pair
that would test whether our geography headline is a latitude band or simply
western Europe. **Prague is at 14.4E, WEST of Vienna at 16.4E.** It does not
extend our eastern reach at all and cannot discriminate. I should have
checked the longitudes before proposing the test.

### Stockholm, about a day

    source     SMHI open data, CC-BY
    history    corrected-archive to 2026-04-30
    current    latest-months, to 2026-08-07, one day behind
    pattern    archive + latest, same shape again

**This is the one design asked for and the one that buys the most.** Every
Phase 1 city sits in the hot half of Europe, so "every city in our set is
elevated" is partly a finding and partly a consequence of which stations we
hold. A Nordic city can produce something our set currently cannot: a city
having an ordinary summer.

**That is worth more than another extreme city.** A set where not everything
is extreme is much harder to dismiss, and VD has already built a fourth
legend rung, "an ordinary summer for it", that no current city occupies.

**Expect the night metric to gate.** Stockholm's tropical-night count will be
near zero, so it will be days-only with a percentile night series, which is
what the optional-blocks template exists for.

## CREDENTIAL-GATED

### London, build-forward

Six routes tested, all fail on currency or licence:

    GHCN-D UKM synoptic   to 2025-08    a year stale
    GHCN-D UKE            to 2026-06    no July, and ECA&D licence
    NOAA ISD hourly       to 2025-08    ~1 year behind globally, not UK
    MIDAS Open daily      to 2025       needs CEDA account AND stops 2025
    MIDAS Open hourly     to 2025       same
    Met Office DataHub    unknown       retention window behind a login

**Needs two free registrations from Kristjan**: a CEDA account for the
1948-2025 MIDAS baseline under the Open Government Licence, and a Met Office
DataHub key for current observations.

**ORDER MATTERS AND IT IS NOT THE OBVIOUS ONE.** If DataHub's retention is
days rather than months, every day we do not collect is permanently lost,
while the MIDAS baseline keeps indefinitely. So: **registrations, then start
the collector, then the baseline at leisure.**

**RETRACTED, SAME DAY: "London is a summer-2027 city" was wrong.**

I wrote it as "settled, not estimated" on 2026-08-09 after six routes failed.
A seventh route works, and I had already built the tool for it.

    SYNOP via OGIMET    03772, 1 May to 9 Aug 2026, 97% of days present
    validated against   the MIDAS baseline itself, 2024 AND 2025
    Tmin @ 06Z          100% within 0.5 C, bias +0.01, worst 0.5
    Tmax @ 18Z          100% within 0.5 C, bias +0.00, worst 0.1
    station identity    MIDAS heathrow / 00708 / 51.479,-0.453
                        SYNOP 03772 Heathrow / 51.479,-0.451

**Not a cross-instrument join.** Same thermometer, same 12-hour windows, a
different transport. The join problem below was real for DataHub's hourly
instantaneous readings and does not exist for SYNOP.

**HOW I GOT IT WRONG, because the mistake generalises.** From ONE station,
Tallinn, I concluded "SYNOP reproduces TMAX exactly and TMIN not at all" and
wrote it into this file three times as the reason to reject Athens, Rome and
London. It is not a property of SYNOP. It is a property of which hours a
given service bulletins its 12-hour extremes at. UK stations report at 09
and 21Z, which is exactly the MIDAS climatological day, and at 06 and 18Z.
Estonia's schedule differs, so Tallinn behaved differently.

**So ATHENS and ROME must be re-tested.** Both have clean histories stopping
at 2025-08, which is precisely London's shape, and both were rejected on a
rule derived from a single counter-example. That rejection is not safe.

**THE OPEN ITEM IS LICENCE, NOT DATA.** OGIMET grants nothing: it is one
person's server, states "we ask you not to abuse it", and asserts copyright
on its own pages. The underlying bulletins are another matter. Under the WMO
Unified Data Policy (Res. 1, Cg-Ext(2021)) the 00/06/12/18Z observations from
RBSN stations are CORE data, free and unrestricted, commercial use included.

That is why the numbers above use 06Z and 18Z rather than the 09Z and 21Z
pair that matches MIDAS more tightly. **The core hours cost nothing**: same
97% coverage, same 5 tropical nights, same 36.4 C warmest day.

**CHECKED, AND IT CAME BACK AGAINST ME.** OSCAR/Surface for Heathrow:

    GBON:Operational, RBON:Operational, GOS General:Operational
    RBSN(S) - deprecated:CLOSED
    RBCN - deprecated:Closed, CLIMAT(C) - deprecated:Closed

**RBSN is closed at Heathrow, so the argument as I stated it fails.** RBSN has
been superseded, and GBON is the designation the Unified Data Policy actually
keys core data to. That is probably a stronger hook than the one I reached
for, and "probably" is not a licence.

Two residual questions I cannot settle from a search result, and neither
should be waved through:

    1  does GBON status carry the whole bulletin, or only the GBON-mandated
       variables? GBON mandates instantaneous temperature, pressure, humidity
       and wind. Our numbers are the 12-hour extremes in SECTION 333, which
       is supplementary rather than mandated, and may not inherit core status
    2  Rome/Ciampino shows RBON but NOT GBON, so even a clean GBON answer
       would not cover all three cities

**The honest position is that all three cities are blocked on the same
question, and it is a question for a human.** The cheap resolution is asking
the Met Office, HNMS and MeteoAM directly, which is the Keskkonnaagentuur
move. I am not signing off any of the three until this is answered.

NOAA is not an alternative route: ISD has no 2026 for this station (404) and
its 2025 stops on 24 August, carrying extreme groups on only 74 of 236 days.

**Baseline: DONE.** Full Heathrow MIDAS record, 1948-2025, 78 files, Open
Government Licence, pulled 2026-08-09 while the CEDA token was live. The day
convention was DERIVED rather than assumed: MIDAS gives a 09h overnight
minimum and a 21h daytime maximum, and against GHCN over 11,000 shared days
the same-calendar-day reading scores 66% while the shifted alternative scores
2%. Residual disagreement is small and scattered, 98.7% of maxima within
0.5 C, with no era-based divergence, so it is rounding or QC rather than two
thermometers.

**THE OPEN PROBLEM IS THE JOIN, NOT THE BASELINE.** London's history is true
12-hour minimum-thermometer readings; its 2026 onward will be hourly
INSTANTANEOUS temperatures, because that is all a 48-hour window can give. A
minimum derived from hourly samples sits warmer than a true minimum, so
ranking future summers against this baseline is a cross-instrument comparison
of the kind that produced the Murcia error.

**It cannot be calibrated yet.** MIDAS stops at 2025 and DataHub holds 48
hours of 2026, so there is NO OVERLAP to measure the offset across. It
becomes measurable when MIDAS publishes its 2026 release, which will overlap
the hourly data being collected from today. The join is verifiable, just not
yet, and today's collection is what makes that check possible.

### Tallinn, build-forward, collecting since 2026-08-08

    archive     no commercially licensed source reaches this summer
                ENE00175051  1919 to 2026-05, ECA&D, non-commercial
                EN000026038  1936 to 2025-08, stopped feeding
    live        Riigi Ilmateenistus observations feed, open, no key
    collector   hourly in GitHub Actions since 2026-08-08
    history     REQUESTED from Keskkonnaagentuur 2026-08-08, awaiting reply

**A summer-2027 city, and saying so plainly matters** because a running
collector feels like progress and is not. Ranking a Tallinn summer needs a
full June to August of samples, and the next one begins in ten months. What
the collector buys is that the 2027 summer will exist when it arrives, which
it would not if collection started then.

**The request to Keskkonnaagentuur asks only for the years before 1991**,
since their site already publishes 1991 onward. That covers the 1991-2020
standard-deviation baseline; the 1971-2000 percentile baseline is the only
genuinely missing piece and the one every other city uses.

**The collector samples an INSTANTANEOUS temperature**, so any daily minimum
derived from it is the lowest sample and sits warmer than a true minimum.
That biases a tropical-night count downward, which is the safe direction,
and it is NOT comparable with archive years measured by a minimum
thermometer. A rank mixing the two would be the Murcia error in a new form.

## BLOCKED

### Warsaw

    IMGW daily climate archive   1951 to MAY 2026, no June or July
    IMGW live API                current hourly instantaneous only,
                                 not daily extremes, no history

**No route to Warsaw's June-July daily minima today.** Worth re-checking
whether IMGW publishes June and July later, since the gap looks like
publication lag rather than policy.

**Warsaw is the city we most want and cannot have.** At 21.0E it is the only
candidate that would settle whether the extreme is a latitude band or a
western-European pattern, because it sits on the boundary the ECMWF anomaly
maps imply. Prague cannot do it and Vienna is already further east.

So the geography headline stays unsettled, and product's fallback of saying
"western Europe" rather than a latitude band is now the likely outcome
rather than the contingency.

## ATTEMPTED AND NOT AVAILABLE

**Recorded so nobody re-runs these searches.** A negative result is a result.

### Athens: RESOLVED 2026-08-09, moved to viable

Previously rejected here on the SYNOP rule that turned out to be wrong.

    station     GHCN GR000016716 = OSCAR 0-20000-0-16716 ATHINAI HELLINIKON
    history     1955 to 2025-08, 30 of 30 baseline years, network 0
    2026        SYNOP, 06Z min and 18Z max
    coverage    99% min, 97% max, 96% both, 1 May to 9 Aug
    agreement   100.0% EXACT against GHCN 2025, worst 0.0 C
    programmes  GBON:Operational, RBON:Operational

**The 100.0% is not independent validation and must not be described as
such.** GHCN network 0 for Greece is built largely from the GTS synoptic
stream, so this is the archive and the bulletins being the same thing rather
than two sources agreeing. That is the RIGHT result for our purpose, which is
whether SYNOP-2026 can extend the GHCN history without a splice, and it is
weaker evidence than London's, where MIDAS is a genuinely separate archive.

    2026 so far   68 tropical nights, warmest 38.3 C, 22 days at or above 35

### Istanbul

    GHCN TU000017062   1929 to 2007      long record, ends 19 years ago
    GHCN TUM00017064   2014 to 2025-08   current-ish, far too short

No viable history at any standard. mgm.gov.tr unreachable.

### Italy: a hard case, not a cheap one

    Rome     GHCN IT000016239   1951 to 2025-08, 30/30 baseline, network 0
                                GOOD HISTORY, STALE. Same shape as Athens
                                and London.
    Milan    GHCN ITE00100554   ends 2008, and network E so ECA&D anyway
    Palermo  GHCN ITM00016410   ends 2009

**No national open archive.** SCIA (ISPRA) and MeteoAM exist as web
interfaces; the MeteoAM API path 404s and ARPA Lombardia is unreachable.
Italy has no equivalent of DWD or Meteo-France: the data is split between a
national agency and regional ARPAs, none publishing a daily archive in the
shape the eight working services do.

**Cost comparison, which is the point.** France, Germany and Switzerland were
about an hour each because the fetcher already existed. Italy is a multi-day
investigation with an uncertain outcome, closer to the UK than to Bordeaux.

**ROME: RESOLVED 2026-08-09.** The paragraph above costed Italy as a multi-day
investigation with an uncertain outcome, "closer to the UK than to Bordeaux".
That was wrong, and it was wrong for the same reason Athens was: it rested on
the SYNOP rule generalised from Tallinn. Corrected, Rome took about twenty
minutes.

    station     GHCN IT000016239 = OSCAR 0-20000-0-16239 ROMA/CIAMPINO
    history     1951 to 2025-08, 30 of 30 baseline years, network 0
    2026        SYNOP, 06Z min and 18Z max
    coverage    99% min, 99% max, 98% both, 1 May to 9 Aug
    agreement   100.0% EXACT against GHCN 2025, worst 0.0 C
    programmes  GOS General:Operational, RBON. NO GBON, unlike Athens
                and Heathrow, which matters for the licence argument below.

Same caveat as Athens: GHCN network 0 is GTS-derived, so this shows the
archive and the bulletins are one thing, not two sources agreeing.

**SYNOP is the more complete record here.** GHCN has only 61 of 92 summer
2025 days for Rome's minimum; SYNOP has the season at 98%.

    2026 so far   54 tropical nights, warmest 38.5 C, 33 days at or above 35

Milan and Palermo are untouched by this and remain blocked: both GHCN records
end long ago (2008, 2009) so there is no history to extend.

**Do not read this as Italy being solved.** One station in Rome is now
reachable. There is still no national daily archive, so a second Italian city
needs the same per-station check rather than a fetcher.

**Italy is also not in the August 2026 event:** Rome +5.9, Milan +7.3,
Palermo +3.9, against Paris +13.6 and Bordeaux +12.8.

### UK and Ireland

Six routes tested for the UK, all failing on currency or licence; see the
London section above. Met Eireann's data host (cli.fusio.net) is unreachable
from here.

**Neither is in the August 2026 event:** Dublin +6.3 against Paris +13.6.

## UNTESTED CANDIDATES

Listed with what needs checking rather than a guess at the answer.

    Helsinki      FMI open data, CC-BY expected. Currency unchecked.
    Oslo          MET Norway Frost API, CC-BY, needs a free key.
    Copenhagen    DMI open data, needs a free key. Currency unchecked.
    Riga/Tallinn/Vilnius   licences and currency both unknown.
    Rome, Milan   Italy has no single national daily open archive;
                  regional services. Expect this to be the hard one.
    Athens        HNMS open data is limited. Unchecked.
    Zurich        MeteoSwiss opendata, recently opened. Unchecked.
    Lisbon        IPMA. Licence unchecked.

**Each is roughly a day if the source behaves like SMHI or CHMI, and
indefinite if it behaves like the UK.** The determinant is always point 3:
whether the current summer is published, not whether the archive is good.

## Recommended order

1. **Stockholm**, because it is verified and it is the only candidate that
   can give the set a city having an ordinary summer.
2. **Prague**, because it is verified and cheap. Not evidence.
3. **London registrations and collector**, because the unrecorded days are
   the only thing here that cannot be recovered later.
4. **Helsinki and Copenhagen**, extending the calibrating northern end.
5. **Warsaw**, re-checked periodically for the June-July publication.

Italy, Greece, Portugal and the Baltics after that, and only after their
currency is confirmed rather than assumed.

## The source cache is the channel, and it exists once

Found by platform 2026-08-09 when CI failed at "Rebuild the payload".

    heat/.cache/src   132 MB, 47 files, gitignored and untracked
    without it        build_city_series.py cannot produce the payload
    so                every city page, the index and the map derive from
                      one untracked directory on one laptop

**IT IS WORSE THAN A MISSING ENTRY POINT, which is how it first reads.**
Three fetchers have no main and no write: meteofrance, aemet, geosphere. They
account for 110.5 of the 132 MB. But adding a main to them would not
reconstitute anything, because they are not the code that built the cache:

    fetch_meteofrance   CITIES lists 5 cities; the channel has 8 French ones.
                        fetch() returns parsed rows; the cache holds
                        mf_<City>_{hist,recent}.csv.gz, a different artifact.
    fetch_aemet         series() returns (date, tmin) with NO tmax; the cache
                        holds [date, min, max] triples.

**So the production path was ad-hoc and was never committed.** A main written
against these modules would emit the wrong shape from the wrong station list,
which is worse than emitting nothing, because it would look like a fix.

**ORDER: STORE IT DURABLY FIRST, REBUILD THE FETCHERS SECOND.** They are not
alternatives. Durability is urgent and cheap; a correct fetcher per service is
real work and can wait a week. Doing the interesting one first leaves the
channel one disk failure from gone for however long the work takes.

    archive   heat-src-cache-2026-08-09.tar.gz, 103 MB, 126 entries
    sha256    3ff9578247fd6c5902536027a69480ddd5226b9dd550d0830c142c867efc4da0
    handed to platform for durable storage, as the London baseline was

**This is the third instance today of the same shape and by far the largest.**
The London MIDAS baseline was 5.8 MB and single-copy until it became a
release. The Tallinn collector wrote into a gitignored directory. This is
132 MB and it is the input to everything. The pattern is not carelessness
about backups; it is that a gitignored path is invisible to the check that
would have caught it, so the data that most needs durability is exactly the
data no guard is watching.

## North Africa and Cyprus: VERIFIED VIABLE, 2026-08-11

Prompted by a reader question on Facebook about North Africa and Cyprus,
which our 41 cities cannot answer: nothing in the set sits south of Malaga
or east of Helsinki.

Five stations pass the bar. Archive from GHCN-Daily, current season from
the station's own SYNOP bulletins, which is the London pattern.

    Casablanca   MOM00060155  ANFA               net M  1957-2025
    Marrakech    MOM00060230  MENARA             net M  1957-2025
    Algiers      AG000060390  ALGER-DAR EL BEIDA net 0  1940-2025
    Tunis        TSM00060715  CARTHAGE           net M  1957-2025
    Larnaca      CY000176090  LARNACA            net 0  1976-2025

All five carry BOTH extremes, reach 2025, and return SYNOP for August 2026.
The four African ones cover 1971-2000 outright.

**CYPRUS IS ONLY REACHABLE BECAUSE OF D-151.** Larnaca starts in 1976 and
cannot cover 1971-2000. Under the ruling made hours earlier it uses the
complete 1991-2020 normal instead. Without that, the one place the reader
actually asked about would have been unbuildable.

**NETWORK E IS THE FILTER THAT MATTERS HERE.** Several of the longest North
African records are ECA&D and therefore non-commercial: Oujda 1910-2025,
Tangier 1912-2025, Biskra 1880-2025, and every Libyan station. Excluding
them is what leaves the five above, and a search that ranked on record
length alone would have picked exactly the ones we may not publish.

**Egypt and Turkey have no usable CITY.** What passes is Siwa, Kharga,
Dakhla, Minya, Rize, Isparta, Sivas, Kastamonu: desert, Nile-valley and
provincial sites. No Cairo, no Alexandria, no Istanbul. So neither country
can be answered with a name a reader recognises, and that is a data fact
rather than a shortage of effort.

**Still to do before any of these is a city:** station identity verified
against the SYNOP coordinates and then day by day, as for Heathrow,
Nottingham, Aldergrove and Dyce; and a current-season route that does not
depend on a volunteer's server, which for the UK meant the Met Office
library and here means asking each national service.

**What this would NOT settle**, and it is the reader's actual question: we
could show Larnaca has more days above its own bar than it used to. We
could not show that this paralyses daytime activity. That is impact
attribution and it belongs to the aftereffects thread.

### North Africa: RULED OUT on maxima completeness, 2026-08-11

I called these three verified viable on record length and SYNOP currency,
then tried to build them. **All three fail, and the check that caught it is
the one I nearly skipped.**

    TMAX May-Aug usable years (>=100 days)
                  1971-2000   1991-2020   recent 15   2025
    Algiers          29/30       10/30        1/15       14
    Casablanca       22/30       11/30        7/15       90
    Tunis            25/30       11/30        2/15       82

**The SYNOP side is perfect.** All three reproduce GHCN exactly where both
hold a value: 100.0% within 0.5 C, worst 0.0, at 06Z and 18Z. The bulletins
are not the problem.

**GHCN's North African MAXIMA are sparse in recent decades.** Algiers has one
usable recent year in fifteen. So a rank of "2026 against its own record"
would rest on a handful of comparison years, and no baseline period is
complete: neither 1971-2000 nor the 1991-2020 alternative D-151 permits.

**Minima are fine.** The asymmetry is what makes this easy to miss: a
station-level check on "does GHCN have data" passes, and only a per-element,
per-year completeness count finds it.

**So the earlier VERIFIED VIABLE line above was wrong**, and it was wrong
because I checked record SPAN and current-season presence, which is points 2
and 3 of the bar, and not whether the years in between carry the element the
metric actually counts. Span is not coverage.

**What would unblock them: a national service, as with the UK.** ONM Algeria,
DGM Morocco and INM Tunisia hold their own archives; GHCN's copy is the thin
one. That is the Rebecca route and it is the only one left.

**Cyprus is untested against this and must be** before it is called viable.
Larnaca's span passes; its per-year element coverage has not been counted.
