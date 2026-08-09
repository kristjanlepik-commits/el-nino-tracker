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

**London is a summer-2027 city unless DataHub's retention surprises us.**
Shipping it now would mean a page whose numbers stop before the heat did, on
the country most likely to check.

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
