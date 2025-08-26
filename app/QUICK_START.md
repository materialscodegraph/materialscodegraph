# Quick Start Guide

## 🚀 Get Started in 60 Seconds

### 1. Install (30 seconds)
```bash
git clone https://github.com/materialscodegraph/materialscodegraph.git
cd materialscodegraph
pip install -r requirements.txt
export MP_API_KEY="your_api_key"  # Get from https://materialsproject.org/api
```

### 2. Run Your First Calculation (30 seconds)
```bash
# Calculate silicon thermal conductivity with one command
python -m cli.mcg plan "Calculate thermal conductivity for silicon at 300K using LAMMPS"
python -m cli.mcg start --plan plan.json
python -m cli.mcg results R12345678
```

## 📖 What Can You Calculate?

### Thermal Conductivity
```bash
# Basic calculation
mcg plan "Calculate thermal conductivity for silicon"

# With temperature range
mcg plan "Get κ for mp-149 from 300K to 800K"

# Using specific method
mcg plan "Use kALDo BTE for silicon thermal conductivity"
```

### Method Comparison
```bash
# Compare MD vs BTE
mcg plan "Compare LAMMPS and kALDo for silicon"
```

## 🧮 Understanding Methods

| Method | Best For | Speed | Result |
|--------|----------|-------|--------|
| **LAMMPS Green-Kubo** | Realistic systems with defects | Hours | κ ≈ 148 W/(m·K) at 300K |
| **kALDo BTE** | Perfect crystals, phonon analysis | Minutes | κ ≈ 200 W/(m·K) at 300K |

## 📊 Example Results

### LAMMPS Output
```
Temperature [K]  |  κ [W/(m·K)]
--------------------------------
     300        |   148.50
     400        |    95.20
     500        |    68.10
```

### kALDo Output (with tensor)
```
Temperature [K]  |  κ_avg  |  κ_xx   κ_yy   κ_zz
-------------------------------------------------
     300        |  200.0  | 204.0  196.0  200.0
     400        |  137.6  | 140.3  134.8  137.6
```

## 🔧 Configuration

Create `.env` file:
```bash
MP_API_KEY=your_materials_project_api_key
MCG_LOG_LEVEL=INFO
```

## 🐳 Docker Quick Start

```bash
# Run everything with Docker
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## 💡 Pro Tips

1. **Natural Language is Flexible**: Try different phrasings - MCG understands many variations
2. **Check Status**: Use `mcg status` to monitor long calculations
3. **Explain Results**: Use `mcg explain` for publication-ready summaries
4. **Full Lineage**: Every calculation is tracked - perfect for reproducible research

## 🆘 Need Help?

- **Examples**: Check `examples/` directory for complete workflows
- **Documentation**: [GitHub Wiki](https://github.com/materialscodegraph/materialscodegraph/wiki)
- **Issues**: [Report bugs](https://github.com/materialscodegraph/materialscodegraph/issues)
- **Discussions**: [Ask questions](https://github.com/materialscodegraph/materialscodegraph/discussions)

## 🎯 Next Steps

1. Try different materials: `mcg plan "Calculate κ for mp-66 diamond"`
2. Explore phonons: `mcg plan "Analyze phonons in silicon using kALDo"`
3. Add your own method: See [CONTRIBUTING.md](CONTRIBUTING.md)

---

**Ready to revolutionize your materials simulations? Let's go! 🚀**