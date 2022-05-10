Changelog
=========

1.2.0 (May 10, 2022)
-----------------------

Inputs can now be a .parquet files.
This can be helpful for preprocessing (e.g. applying a machine learning algorithm).
The standard path is still a glob pattern for .root files.

1.1.0 (January 25, 2022)
-----------------------

- An additional CLI is introduced: `higgstables-df`.
  It leverages the new `DfFromFiles` class.
  While the (name-giving) step of building tables with the event counts in
  categories is replaced by a per-event DataFrame, the pre-selection machinery
  is reused/shared between `higgstables-df` and `higgstables`.
- A new optional top level field (under _higgstables_) is introduced in the
  config yaml file: _df_.
  Configuration options that are unique to `DfFromFiles` are located under the
  _df_ field.

1.0.0 (July 17, 2021)
-----------------------

The `higgstables` CLI should now be stable.
Important changes should appear in the changelog.
