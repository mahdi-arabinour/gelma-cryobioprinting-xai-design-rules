# Run order

Run all commands from the repository root.

## 1. Create the environment

Using Conda:

```bash
conda env create -f environment.yml
conda activate cryobioprinting-xai
```

Or using pip:

```bash
python -m pip install -r requirements.txt
```

## 2. Rebuild the standardized dataset

```bash
python scripts/prepare_data.py
```

This step reads the source-style reconstruction and rewrites the standardized processed table. It does not impute any missing formulation.

## 3. Validate the dataset

```bash
python scripts/validate_dataset.py
```

The validator checks required columns, row count, unique formulation identifiers, allowed categories and concentrations, viability bounds, categorical flags, and the four expected missing conditions.

## 4. Run the analysis

```bash
python scripts/run_pipeline.py
```

The complete pipeline writes tables, figures, the final serialized model, model metadata, an export manifest, and `outputs_package.zip`.

## 5. Compare with expected results

Review `docs/EXPECTED_RESULTS.md` and the generated files under `outputs/tables/`.

## Notebook route

The notebook in `notebooks/` executes the same scripts. The command-line route is preferred for a clean reproducibility check because it makes the working directory and dependency state explicit.
