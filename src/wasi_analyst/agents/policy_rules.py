def simple_mean_reversion(price, avg, strength=0.2):
    # positivo -> comprar; negativo -> vender
    return (avg - price) / max(1e-6, avg) * strength
