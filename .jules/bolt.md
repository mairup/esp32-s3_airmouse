## 2024-05-01 - Lack of Toit compiler in test environment
**Learning:** The Toit compiler is not installed in the execution environment, so traditional `toit compile` or `toit run` commands cannot be used for verification. Verification must rely on careful visual inspection and python simulations of logic.
**Action:** Do not attempt to run `toit` commands. Rely on manual review and python scripts to test small logical chunks if needed.
