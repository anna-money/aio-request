## v0.2.6 (2025-12-03)

* [Use LiteralString for url parameter in request functions](https://github.com/anna-money/aio-request/pull/310)


## v0.2.6a1 (2025-12-03)

* [Use LiteralString for url parameter in request functions](https://github.com/anna-money/aio-request/pull/310)


## v0.2.5 (2025-12-01)

* [Import PercentileBasedRequestAttemptDelaysProvider only conditionally](https://github.com/anna-money/aio-request/pull/309)


## v0.2.4 (2025-12-01)

* [Retry tcp level connect errors](https://github.com/anna-money/aio-request/pull/308)
* [Percentile based delays](https://github.com/anna-money/aio-request/pull/304)


## v0.2.4a1 (2025-11-29)

* [Percentile based delays](https://github.com/anna-money/aio-request/pull/304)


## v0.2.3 (2025-11-23)

* [Migrate to modern tooling + python 3.14](https://github.com/anna-money/aio-request/pull/301)


## v0.2.2 (2025-07-31)

* [Now json() could parse empty body when using httpx transport](https://github.com/anna-money/aio-request/pull/296)


## v0.2.1 (2025-01-09)

* [Increase metrics buckets precision](https://github.com/anna-money/aio-request/pull/287)
* [Expose methods to build requests](https://github.com/anna-money/aio-request/pull/288)
* [Transport metrics to track individual requests](https://github.com/anna-money/aio-request/pull/289)


## v0.2.0 (2025-01-09)

* [Support httpx transport](https://github.com/anna-money/aio-request/pull/221)
* Drop python 3.9/3.10 support, support only 3.11/3.12/3.13. Related PRs: [#222](https://github.com/anna-money/aio-request/pull/222), [#266](https://github.com/anna-money/aio-request/pull/266), [#275](https://github.com/anna-money/aio-request/pull/275)
* Deprecation of MetricsProvider interface. For the backward compatibility, prometheus-client is conditionally imported. To use it, install prometheus-client. Related PRs: [#271](https://github.com/anna-money/aio-request/pull/271), [#218](https://github.com/anna-money/aio-request/pull/218), [#268](https://github.com/anna-money/aio-request/pull/268)
* [Removal of unused Client interface](https://github.com/anna-money/aio-request/commit/fe75660af8e7520a6fa5143f982c5aacd2ea079a)
* [Do not retry low timeout response](https://github.com/anna-money/aio-request/pull/276)
* Refactoring around request enrichers and deprecation of setup_v2. Related PRs: [#277](https://github.com/anna-money/aio-request/pull/277), [#282](https://github.com/anna-money/aio-request/pull/282), [#285](https://github.com/anna-money/aio-request/pull/285)
* [Deadline provider for sequential strategy](https://github.com/anna-money/aio-request/pull/284)
* [Limit deadline split between attempts by a factor](https://github.com/anna-money/aio-request/pull/286)


## v0.1.34 (2024-11-05)

* [Try to get metrics provider from transport in setup_v2 if no metrics provider is passed](https://github.com/anna-money/aio-request/pull/280)


## v0.1.33 (2024-10-29)

* [Only yarl >= 1.12 is supported](https://github.com/anna-money/aio-request/commit/1a443f2ec6637bbfb86b717ac03b56a3ff0650b8)


## v0.1.32 (2024-10-18)

* [Endpoint provider](https://github.com/anna-money/aio-request/pull/270)


## v0.1.31 (2024-09-05)

* [Only yarl < 1.9.10 is supported](https://github.com/anna-money/aio-request/commit/ed8141e6a7a6b30d46190da4514f5ddb8e8db2ca)


## v0.1.30 (2023-07-23)

* [Removal of tracing support](https://github.com/anna-money/aio-request/pull/213)
* [Drop python 3.8 support](https://github.com/anna-money/aio-request/pull/216)


## v0.1.29 (2023-04-27)

* [Stop losing redirects params in headers update](https://github.com/anna-money/aio-request/pull/204)


## v0.1.28 (2023-04-27)

* [Add allow_redirects and max_redirects options to request](https://github.com/anna-money/aio-request/pull/195)


## v0.1.27 (2023-02-16)

* [Maintenance release](https://github.com/anna-money/aio-request/compare/v0.1.26...v0.1.27)


## v0.1.26 (2022-11-02)

* [Add python 3.11 support](https://github.com/anna-money/aio-request/pull/159)


## v0.1.25 (2022-08-25)

* [Reverted: URL-encode path_parameters](https://github.com/anna-money/aio-request/pull/155) - let user
  decide what to do


## v0.1.24 (2022-07-04)

* [URL-encode path_parameters](https://github.com/anna-money/aio-request/pull/146)


## v0.1.23 (2022-02-08)

* [Reject throttling(too many requests) status code](https://github.com/anna-money/aio-request/pull/123)


## v0.1.22 (2022-01-08)

* Return default json expected content_type to "application/json"
* [Release aiohttp response instead of close](https://github.com/Pliner/aio-request/pull/108)
* [Validate json content-type](https://github.com/Pliner/aio-request/pull/109)


## v0.1.21 (2022-01-05)

* Content type should be None in Response.json()


## v0.1.20 (2022-01-05)

* [Do not expect json content type by default](https://github.com/Pliner/aio-request/pull/106)


## v0.1.19 (2021-11-01)

* [Support async-timeout 4.0+](https://github.com/Pliner/aio-request/pull/86)


## v0.1.18 (2021-09-08)

* [Reexport explicitly](https://github.com/Pliner/aio-request/pull/74)


## v0.1.17 (2021-09-01)

* [Fix patch/patch_json visibility](https://github.com/Pliner/aio-request/pull/73)


## v0.1.16 (2021-09-01)

* [Support patch method](https://github.com/Pliner/aio-request/pull/72)


## v0.1.15 (2021-09-01)

* [Clean up resources in single shield](https://github.com/Pliner/aio-request/pull/71)


## v0.1.14 (2021-08-18)

* [Keys should be materialized if dict is changed in loop](https://github.com/Pliner/aio-request/pull/66)


## v0.1.13 (2021-08-15)

* [Circuit breaker](https://github.com/Pliner/aio-request/pull/65)


## v0.1.12 (2021-07-21)

* [Basic repr implementation](https://github.com/Pliner/aio-request/commit/adaa4888c3d372fa65f3dd5eb6113ab68f46de24)


## v0.1.11 (2021-07-21)

* Fix Request.update_headers, add Request.extend_headers [#59](https://github.com/Pliner/aio-request/pull/59)


## v0.1.10 (2021-07-20)

* Add Response.is_json property to check whether content-type is json compatible [#58](https://github.com/Pliner/aio-request/pull/58)
* Tracing support [#54](https://github.com/Pliner/aio-request/pull/54), 
* [Configuration](https://github.com/Pliner/aio-request/commit/f0e1904f4d87daf7c242a834168c0f1b25dd86d5) of a new pipeline
