<?php
$labName = 'ChemLab Studio';
$experiments = [
    ['name' => 'Acid + Base Neutralisation', 'level' => 'Beginner', 'color' => '#ff8066'],
    ['name' => 'Copper Sulfate Reaction', 'level' => 'Intermediate', 'color' => '#36c5f0'],
    ['name' => 'pH Indicator Test', 'level' => 'Beginner', 'color' => '#a78bfa']
];
?><!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="ChemLab Studio interactive chemistry practical laboratory simulation">
    <meta name="theme-color" content="#07111f">
    <title><?= htmlspecialchars($labName) ?> | Interactive Chemistry Lab</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="style.css">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark fixed-top glass-nav" aria-label="Main navigation">
    <div class="container">
        <a class="navbar-brand fw-bold d-flex align-items-center gap-2" href="#home"><span class="brand-mark">⚗</span> ChemLab <span class="brand-accent">Studio</span></a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNav" aria-controls="mainNav" aria-expanded="false" aria-label="Toggle navigation"><span class="navbar-toggler-icon"></span></button>
        <div class="collapse navbar-collapse" id="mainNav">
            <ul class="navbar-nav ms-auto align-items-lg-center gap-lg-3">
                <li class="nav-item"><a class="nav-link active" href="#home">Home</a></li>
                <li class="nav-item"><a class="nav-link" href="#experiments">Experiments</a></li>
                <li class="nav-item"><a class="nav-link" href="#lab">Virtual Lab</a></li>
                <li class="nav-item"><a class="nav-link" href="#safety">Safety</a></li>
                <li class="nav-item"><button class="btn btn-outline-light btn-sm rounded-pill px-3" id="themeBtn" type="button">☼ Light mode</button></li>
            </ul>
        </div>
    </div>
</nav>

<main id="home">
    <section class="hero-section">
        <div class="container position-relative">
            <div class="row align-items-center g-5">
                <div class="col-lg-7">
                    <div class="eyebrow"><span class="pulse-dot"></span> DIGITAL PRACTICAL LABORATORY</div>
                    <h1>Discover the <span class="gradient-text">science</span> behind every reaction.</h1>
                    <p class="hero-copy">Learn chemistry by doing. Mix safe virtual chemicals, observe realistic reactions, and build confidence before entering a physical laboratory.</p>
                    <div class="d-flex flex-wrap gap-3">
                        <a href="#lab" class="btn btn-primary btn-lg rounded-pill px-4">Enter the lab <span>→</span></a>
                        <a href="#experiments" class="btn btn-ghost btn-lg rounded-pill px-4">Explore practicals</a>
                    </div>
                    <div class="hero-stats mt-5 d-flex gap-4 flex-wrap">
                        <div><strong>12+</strong><span>simulations</span></div><div><strong>100%</strong><span>safe to try</span></div><div><strong>24/7</strong><span>learn anywhere</span></div>
                    </div>
                </div>
                <div class="col-lg-5">
                    <div class="hero-visual" aria-label="Animated laboratory illustration">
                        <div class="orbit orbit-one"></div><div class="orbit orbit-two"></div>
                        <div class="flask-hero"><div class="flask-neck"></div><div class="flask-liquid"></div><div class="bubble b1"></div><div class="bubble b2"></div><div class="bubble b3"></div></div>
                        <div class="floating-card card-top">✦ <span>Observe</span><b>Live reactions</b></div>
                        <div class="floating-card card-bottom">🛡 <span>Safety first</span><b>Risk-free learning</b></div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <section class="section-pad" id="experiments">
        <div class="container">
            <div class="section-heading"><div><div class="eyebrow">CURATED PRACTICALS</div><h2>Choose your next experiment</h2></div><p>Start simple, then level up your laboratory skills.</p></div>
            <div class="row g-4">
                <?php foreach ($experiments as $index => $experiment): ?>
                <div class="col-md-4"><article class="experiment-card" style="--card-color: <?= $experiment['color'] ?>"><div class="card-number">0<?= $index + 1 ?></div><div class="experiment-icon"><?= $index === 0 ? '⚖' : ($index === 1 ? '◈' : '◉') ?></div><span class="level-pill"><?= htmlspecialchars($experiment['level']) ?></span><h3><?= htmlspecialchars($experiment['name']) ?></h3><p><?= $index === 0 ? 'Explore how an acid and a base combine to form salt and water.' : ($index === 1 ? 'Observe a colour change and solid formation in a controlled reaction.' : 'Use a virtual indicator to classify unknown solutions by pH.') ?></p><a href="#lab" class="text-link choose-experiment" data-experiment="<?= $index ?>">Open practical <span>↗</span></a></article></div>
                <?php endforeach; ?>
            </div>
        </div>
    </section>

    <section class="lab-section" id="lab">
        <div class="container">
            <div class="lab-header"><div><div class="eyebrow">INTERACTIVE WORKSPACE</div><h2>Virtual chemistry bench</h2><p>Choose bottles, add them to the beaker, then run the reaction.</p></div><div class="lab-status"><span class="status-light"></span> Simulation ready</div></div>
            <div class="lab-panel">
                <div class="row g-0">
                    <aside class="col-lg-4 chemical-sidebar">
                        <div class="side-title"><h3>Reagent shelf</h3><span id="bottleCount">0/2 selected</span></div>
                        <p class="small-muted">Click a bottle to add it to your beaker.</p>
                        <div class="bottle-list" id="bottleList">
                            <button class="chemical-bottle" data-chemical="acid" type="button"><span class="bottle bottle-acid"><i></i></span><span><b>Hydrochloric Acid</b><small>HCl · acidic</small></span><em>+</em></button>
                            <button class="chemical-bottle" data-chemical="base" type="button"><span class="bottle bottle-base"><i></i></span><span><b>Sodium Hydroxide</b><small>NaOH · alkaline</small></span><em>+</em></button>
                            <button class="chemical-bottle" data-chemical="indicator" type="button"><span class="bottle bottle-indicator"><i></i></span><span><b>Universal Indicator</b><small>pH indicator</small></span><em>+</em></button>
                            <button class="chemical-bottle" data-chemical="copper" type="button"><span class="bottle bottle-copper"><i></i></span><span><b>Copper Sulfate</b><small>CuSO₄ · salt</small></span><em>+</em></button>
                        </div>
                        <div class="safety-mini"><span>🛡</span><div><b>Safety mode on</b><small>This is a safe visual simulation.</small></div></div>
                    </aside>
                    <div class="col-lg-8 bench-area">
                        <div class="bench-toolbar"><span>Experiment: <b id="activeExperiment">Free exploration</b></span><button class="reset-btn" id="resetBtn" type="button">↻ Reset bench</button></div>
                        <div class="workspace">
                            <div class="measurement"><span>100</span><span>75</span><span>50</span><span>25</span><span>0</span></div>
                            <div class="beaker-wrap"><div class="beaker" id="beaker"><div class="beaker-liquid" id="beakerLiquid"></div><div class="reaction-bubble rb1"></div><div class="reaction-bubble rb2"></div><div class="reaction-bubble rb3"></div><div class="beaker-mark m1"></div><div class="beaker-mark m2"></div><div class="beaker-mark m3"></div></div><div class="beaker-base"></div><div class="drop-zone-text" id="dropZoneText">Add reagents<br><small>to begin</small></div></div>
                            <div class="bench-tools"><div class="tool-item"><div class="tool-icon">⚗</div><span>Beaker</span></div><div class="tool-item"><div class="tool-icon thermometer">♨</div><span>Observe</span></div><div class="tool-item"><div class="tool-icon">⌁</div><span>Stir</span></div></div>
                        </div>
                        <div class="result-bar" id="resultBar"><div><span class="result-icon">i</span><span id="resultText">Select two compatible reagents to see a simulated reaction.</span></div><button id="reactBtn" class="btn btn-primary rounded-pill px-4" type="button" disabled>Run reaction <span>→</span></button></div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <section class="section-pad safety-section" id="safety"><div class="container"><div class="row align-items-center g-5"><div class="col-lg-6"><div class="eyebrow">LABORATORY ESSENTIALS</div><h2>Good science starts with good habits.</h2><p class="lead-muted">Our simulations teach the process, not just the result. Follow each step, observe carefully, and always respect real-world laboratory safety.</p><div class="safety-points"><div><span>01</span><p><b>Wear protection</b><br>Goggles, gloves, and a lab coat are essential in a physical lab.</p></div><div><span>02</span><p><b>Read labels</b><br>Understand chemical properties before handling any substance.</p></div><div><span>03</span><p><b>Never taste chemicals</b><br>Use safe observation methods and follow your instructor's guidance.</p></div></div></div><div class="col-lg-6"><div class="safety-visual"><div class="shield">🛡</div><div class="ring ring-a"></div><div class="ring ring-b"></div><span class="label label-a">Observe</span><span class="label label-b">Protect</span><span class="label label-c">Learn</span></div></div></div></div></section>
</main>
<footer><div class="container d-flex flex-wrap justify-content-between align-items-center gap-3"><a class="navbar-brand fw-bold" href="#home">⚗ ChemLab <span class="brand-accent">Studio</span></a><p class="mb-0">Built for curious minds · <?= date('Y') ?></p><span class="footer-note">Interactive learning simulation</span></div></footer>
<div class="toast-container position-fixed bottom-0 end-0 p-3"><div id="labToast" class="toast" role="status"><div class="toast-body"></div></div></div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script><script src="script.js"></script>
</body>
</html>