# Importing libraries
import pymc as pm
import numpy as np
import pandas as pd
import arviz as az # Para análise e armazenamento da inferência

# --- Configuration Parameters ---
RANDOM_SEED = 42
CHAINS = 4
DRAWS = 2000
TUNE = 1000

def run_bayesian_model(df_agg: pd.DataFrame):
    """
    Zero-Inflated Baeysian Model for ARPU (CVR and ARPC).
    """
    
    # Data preparation
    control_data = df_agg[df_agg['variant_name'] == 'control']
    variant_data = df_agg[df_agg['variant_name'] == 'variant']
    
    # CVR Model (Conversion Rate) - Beta-Binomial
    N_control = control_data['converted'].count()
    y_control = control_data['converted'].sum()
    N_variant = variant_data['converted'].count()
    y_variant = variant_data['converted'].sum()
    
    # ARPC Model (Average Revenue of Converting Users) - Gamma (for revenue > 0)
    # Filters only postive revenue
    revenue_control = control_data[control_data['converted'] == 1]['total_revenue'].values
    revenue_variant = variant_data[variant_data['converted'] == 1]['total_revenue'].values

    # --- Model Construction ---
    with pm.Model() as ab_test_model:
        
        # A) Priors for CVR - Beta-Binomial
        # 'p' represents the underlying probability of conversion. (CVR)
        p_control = pm.Beta('p_control', alpha=1, beta=1) # Uniform prior for the proportion
        p_variant = pm.Beta('p_variant', alpha=1, beta=1)
        
        # Likelihood CVR (Binomial: number of successes'y' given 'N' trials and probability 'p')
        # We use N_conversions (successes) in N_users (trials)
        pm.Binomial('y_control', n=N_control, p=p_control, observed=y_control)
        pm.Binomial('y_variant', n=N_variant, p=p_variant, observed=y_variant)

        # B) Priors for ARPC (Receita) - Gamma (to model assimetric positive values)
        # 'mu' is the rate parameter (scale) of the Gamma Distribution. We use a prior log-normal to guarantee it is positive
        mu_control = pm.HalfNormal('mu_control', sigma=1)
        mu_variant = pm.HalfNormal('mu_variant', sigma=1)
        
        # Alpha (concentration/shape) is the shared parameter that defines the distribution's shape
        alpha = pm.HalfNormal('alpha', sigma=1)

        beta_control = pm.Deterministic('beta_control', alpha / mu_control)
        beta_variant = pm.Deterministic('beta_variant', alpha / mu_variant)
        
        # Likelihood ARPC (Gamma) - Used only on revenue > 0 data
        pm.Gamma('revenue_control', alpha=alpha, beta=beta_control, observed=revenue_control)
        pm.Gamma('revenue_variant', alpha=alpha, beta=beta_variant, observed=revenue_variant)

        # C) Derived Variables (Posterior Predictive)
        # 1. CVR Lift
        cvr_lift = pm.Deterministic('cvr_lift', p_variant - p_control)
        
        # 2. ARPC Lift
        arpc_lift = pm.Deterministic('arpc_lift', mu_variant - mu_control)

        # 3. ARPU (The final business result)
        # ARPU = CVR * ARPC. Note that p_control is the probability of conversion (CVR) and mu_control is the average revenue *if* converted (ARPC)
        arpu_control = pm.Deterministic('arpu_control', p_control * mu_control)
        arpu_variant = pm.Deterministic('arpu_variant', p_variant * mu_variant)
        
        # 4. ARPU Lift
        arpu_lift = pm.Deterministic('arpu_lift', arpu_variant - arpu_control)

        # --- Inference Execution ---
        # pm.sample() usa o No-U-Turn Sampler (NUTS)
        idata = pm.sample(
            draws=DRAWS, 
            tune=TUNE, 
            chains=CHAINS, 
            random_seed=RANDOM_SEED, 
            target_accept=0.9 # Improve the precision in complex models
        )
        
    return idata

if __name__ == '__main__':
    # Reading the data
    try:
        data = pd.read_csv("data/processed/data_processed.csv") 
    except Exception as e:
        print(f"❌Erro while loading the data: {e}")
        exit()

    print("Intializing the Bayesian Modeling...")
    
    # Calling the modeling function
    idata = run_bayesian_model(data)

    # Saving the result
    try:
        az.to_netcdf(idata, "data/processed/bayesian_trace.nc")
        print("✅ Inference saved at data/processed/bayesian_trace.nc")
    except Exception as e:
        print(f"❌ Error while saving the inference: {e}")