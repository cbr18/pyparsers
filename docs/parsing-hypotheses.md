# Parsing Hypotheses

This file tracks active parsing hypotheses and the observations that support them.
It is intentionally short and operational.

## Dongchedi

### Confirmed: detail pages use `sku_id`, not list `car_id`

Observations:
- Current list responses expose both `car_id` and `sku_id`.
- Local live example from `GET /cars/page/1` returned entries like:
  - `car_id=58604`
  - `sku_id=23384046`
- Direct detail check with list `car_id`:
  - `GET /cars/car/58604`
  - returned a generic Dongchedi page with `is_banned=true`, no images, no registration.
- Direct detail check with list `sku_id`:
  - `GET /cars/car/23384046`
  - returned a real detailed car with images, `first_registration_time`, dealer info and dimensions.

Implication:
- Dongchedi detail parsing should use `sku_id` as the primary detail identifier.
- Any probe or API endpoint that uses list `car_id` as the direct detail URL parameter will misclassify healthy cards as blocked.

### Confirmed: current mobile fallback is not reliable for these IDs

Observations:
- Live request to `https://m.dongchedi.com/usedcar/33528` returned a Next.js `404` page, not a car detail page.
- The `__NEXT_DATA__` payload on that response had `page=/404`.

Implication:
- The current mobile fallback cannot be treated as a trustworthy fallback for IDs taken directly from list `car_id`.
- Mobile fallback should not be the main diagnostic signal for "blocked".

### Confirmed: `__NEXT_DATA__` can exist even when the page is a 404 shell

Observations:
- Live desktop request to `https://www.dongchedi.com/usedcar/33528` returned `page=/404`.
- The payload still contained `props.pageProps`, but only metadata keys like:
  - `__hasUrlCity`
  - `is_gray`
  - `has_gray`
  - `clientIp`
  - `sensitiveSeriesIdList`
- There was no `skuDetail` on that page.

Implication:
- The presence of `__NEXT_DATA__` alone does not mean that we are on a real detail page.
- Parser diagnostics should distinguish:
  - page shell present
  - real detail payload present

### Working hypothesis: some historical saved HTML is still structurally valid

Observations:
- Local file `pyparsers/examples/dongchediuserdcar.htm` contains a real detail page.
- It has canonical URL `https://www.dongchedi.com/usedcar/18566976`.
- Its `__NEXT_DATA__` payload uses `page=/usedcar/detail` and contains a rich detail object with:
  - `sku_id`
  - `shop_info`
  - `sh_car_desc`
  - images and report blocks

Implication:
- The page model itself still supports rich server-rendered detail payloads.
- The main regression currently looks like wrong identifier selection first, and schema drift second.

### Working hypothesis: app/mobile APIs probably exist, but exact used-car detail endpoint is not localized yet

Observations:
- Desktop and mobile pages declare CSP domains such as:
  - `*.dcarapi.com`
  - `*.dcdapp.com`
  - `*.snssdk.com`
- This suggests app/backend APIs are present in the ecosystem.
- No stable used-car detail endpoint has been extracted yet from live detail page HTML with low-request probing.

Implication:
- A dedicated app API may exist and may be more stable than page scraping.
- Next step should be careful extraction from script bundles or network traces for one known-good `sku_id`, without high request volume.

### Confirmed: detail page itself uses internal JSON endpoints, and `major` is a working parser path

Observations:
- The live `/usedcar/detail` bundle calls:
  - `/motor/pc/sh/detail/major`
  - `/motor/pc/sh/detail/card_list`
- Bundle evidence:
  - `Promise.allSettled([Vi({sku_id:d,city_name:s},l),Li({sku_id:d,city_name:s},l), ...])`
  - `Vi(...)` resolves to `/motor/pc/sh/detail/major?...`
  - `Li(...)` resolves to `/motor/pc/sh/detail/card_list?...`
- Direct request to:
  - `https://www.dongchedi.com/motor/pc/sh/detail/major?sku_id=<sku_id>`
  - returns `200 application/json` with a rich `data` payload.
- The endpoint works even without `city_name`.
- Local parser verification after switching to API-first:
  - `/cars/car/{sku_id}` returns real detail data
  - logs show `[DETAIL API] Успешно получены данные...`
  - `/blocked` returns `blocked=0`

Implication:
- The most stable current Dongchedi detail method is no longer HTML scraping.
- Primary detail strategy should be:
  - `sku_id`
  - `/motor/pc/sh/detail/major`
  - HTML / mobile only as fallback
- `card_list` is useful for page completeness, but not required for the core parser contract right now.

## Current safe methods

- Use list endpoint sparingly to get one fresh `sku_id`.
- Use Dongchedi detail parsing with `sku_id`, not `car_id`.
- Prefer Dongchedi detail JSON API:
  - `/motor/pc/sh/detail/major?sku_id=<sku_id>`
- Treat mobile-web fallback as diagnostic-only.
- Treat `__NEXT_DATA__` without `skuDetail` or equivalent rich payload as a page-shell/404 condition, not as a successful detail fetch.
- Prefer Che168 signed search API for list:
  - `https://api2scsou.che168.com/api/v11/search`
  - with RN-style defaults and `_sign`
- Treat Selenium / Playwright as Che168 list fallback only, not as the main path.

## Che168

### Confirmed: detailed API path is healthier than list page scraping

Observations:
- Multiple live runs produced successful detailed parses with:
  - `piclist`
  - `getparamtypeitems`
  - `getcarinfo`
- Example log pattern:
  - images found from `piclist`
  - power/torque/transmission/fuel type extracted
  - `first_registration_time` extracted
- Detailed parsing can succeed even when desktop HTML URLs time out.

Implication:
- `che168` detailed should rely on API-first extraction.
- Desktop Selenium should only be a fallback for missing gallery or blocked API, not the default first step.

### Confirmed: list-page instability is currently the main che168 weak point

Observations:
- Selenium list runs intermittently fail with `net::ERR_CONNECTION_CLOSED`.
- The same list endpoint can succeed on one run and fail on another run from the same environment.
- When list succeeds, it returns a valid page with about 56 cars.

Implication:
- The main instability is not in detailed parsing but in list acquisition.
- Smoke probes that start with list are only as reliable as this list-page transport.

### Confirmed: requests/curl HTML fetch is blocked by anti-bot JS, not suitable as primary list fallback

Observations:
- A direct `curl` to the che168 list URL returns anti-bot JavaScript, not the car list HTML.
- This means plain requests/curl cannot currently replace browser automation for list parsing.

Implication:
- A non-browser fallback for che168 list is not yet available from the current evidence.
- Browser-based list parsing remains necessary for now.

### Confirmed: Playwright fallback now uses system Chromium, but upstream can still close the connection

Observations:
- Initial Playwright fallback failed because the bundled Playwright browser was not installed.
- After switching Playwright launch to system Chromium, that operational error disappeared.
- The current failure mode is now upstream `Page.goto: net::ERR_CONNECTION_CLOSED`, which is external/network-side rather than missing local browser binaries.

Implication:
- The Playwright fallback is now operationally wired correctly.
- Remaining che168 list failures are now true upstream/anti-bot instability, not local environment misconfiguration.

### Confirmed: mobile app search API exists and can replace browser list scraping

Observations:
- The mobile RN bundle exposes:
  - `https://api2scsou.che168.com/api/v11/search`
- The same bundle contains the signing flow:
  - `getencode(...) -> _apsp(...)`
  - defaults:
    - `_appid=2sc.m`
    - `v=11.41.5`
    - `_subappid=""`
  - signing secret after deobfuscation:
    - `com.rnw.www`
- Low-noise live checks showed:
  - without `_appid` -> `returncode=103`
  - with `_appid` but wrong/no sign -> `returncode=107`
  - with reproduced sign -> `returncode=0` and real `result.carlist`
- Local parser verification after switching to API-first:
  - `GET /cars/page/1` returns `Success (signed API)`
  - `GET /blocked` returns `blocked=0`
  - integration smoke passes

Implication:
- Browser automation is no longer the preferred primary list strategy for Che168.
- The current best generic list path is:
  - signed mobile app API `api/v11/search`
  - Selenium / Playwright only as fallback
- This reduces both fragility and request cost compared with browser-first scraping.

### Working hypothesis: `/series/used-car-search` is secondary or route-specific, not the generic list endpoint

Observations:
- The bundle references `/api/v11/series/used-car-search`.
- A direct low-noise probe with minimal params returned `404`.
- In contrast, `/api/v11/search` succeeded immediately once the signature was reproduced correctly.

Implication:
- Keep `/api/v11/search` as the generic marketplace list endpoint.
- Revisit `/series/used-car-search` only if a later feature needs series-scoped search behavior.
