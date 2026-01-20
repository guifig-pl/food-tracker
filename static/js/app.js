/**
 * Food Tracker - Main Application JavaScript
 * Mobile-first PWA for tracking meals and nutrition
 */

// ============================================
// App State
// ============================================

const state = {
    currentDate: new Date(),
    currentView: 'dashboard',
    selectedFood: null,
    settings: {},
    analyticsTab: 'weekly',
    foodsTab: 'all',
    chart: null,
    // Multi-ingredient meal state
    mealMode: 'quick',  // 'quick' or 'multi'
    multiMealIngredients: [],  // Array of {food, amount_grams, calories, protein, carbs, fats}
    selectedIngredientFood: null
};

// ============================================
// API Helper
// ============================================

const API = {
    baseUrl: '/api',

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: { 'Content-Type': 'application/json' },
            ...options
        };

        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'API request failed');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    get(endpoint) {
        return this.request(endpoint);
    },

    post(endpoint, body) {
        return this.request(endpoint, { method: 'POST', body });
    },

    put(endpoint, body) {
        return this.request(endpoint, { method: 'PUT', body });
    },

    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
};

// ============================================
// Utility Functions
// ============================================

function formatDate(date, format = 'display') {
    const d = new Date(date);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (format === 'api') {
        return d.toISOString().split('T')[0];
    }

    if (isSameDay(d, today)) {
        return 'Today';
    }
    if (isSameDay(d, yesterday)) {
        return 'Yesterday';
    }

    return d.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric'
    });
}

function isSameDay(d1, d2) {
    return d1.getDate() === d2.getDate() &&
           d1.getMonth() === d2.getMonth() &&
           d1.getFullYear() === d2.getFullYear();
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function $(selector) {
    return document.querySelector(selector);
}

function $$(selector) {
    return document.querySelectorAll(selector);
}

// ============================================
// Toast Notifications
// ============================================

function showToast(message, duration = 3000) {
    const toast = $('#toast');
    toast.querySelector('.toast-message').textContent = message;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, duration);
}

// ============================================
// Modal Management
// ============================================

function openModal(modalId) {
    $('#modalOverlay').classList.add('active');
    $(`#${modalId}`).classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal(modalId) {
    $('#modalOverlay').classList.remove('active');
    $(`#${modalId}`).classList.remove('active');
    document.body.style.overflow = '';
}

function closeAllModals() {
    $$('.modal').forEach(modal => modal.classList.remove('active'));
    $('#modalOverlay').classList.remove('active');
    document.body.style.overflow = '';
}

// ============================================
// View Navigation
// ============================================

function switchView(viewName) {
    state.currentView = viewName;

    $$('.view').forEach(view => view.classList.remove('active'));
    $(`#${viewName}View`).classList.add('active');

    $$('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.view === viewName);
    });

    // Load view-specific data
    if (viewName === 'dashboard') {
        loadDashboard();
    } else if (viewName === 'analytics') {
        loadAnalytics();
    } else if (viewName === 'foods') {
        loadFoods();
    } else if (viewName === 'settings') {
        loadSettings();
    }
}

// ============================================
// Dashboard
// ============================================

async function loadDashboard() {
    try {
        const dateStr = formatDate(state.currentDate, 'api');
        const data = await API.get(`/progress/daily?date=${dateStr}`);

        updateDateDisplay();
        updateProgressCards(data.progress);
        updateMealsList(data.meals, data.multi_meals || []);
        updateOffDayBanner(data.off_day);
    } catch (error) {
        showToast('Failed to load dashboard');
        console.error(error);
    }
}

function updateDateDisplay() {
    $('#currentDate').textContent = formatDate(state.currentDate);
}

function updateProgressCards(progress) {
    const { totals, targets, percentage, deficit_surplus } = progress;

    // Calories
    $('#caloriesValue').textContent = `${Math.round(totals.calories)} / ${targets.calories}`;
    $('#caloriesBar').style.width = `${Math.min(percentage.calories, 100)}%`;

    // Deficit/Surplus
    const deficitEl = $('#deficitSurplus');
    if (deficit_surplus > 0) {
        deficitEl.textContent = `+${Math.round(deficit_surplus)} surplus`;
        deficitEl.className = 'deficit-surplus surplus';
    } else if (deficit_surplus < 0) {
        deficitEl.textContent = `${Math.round(Math.abs(deficit_surplus))} remaining`;
        deficitEl.className = 'deficit-surplus deficit';
    } else {
        deficitEl.textContent = 'On target!';
        deficitEl.className = 'deficit-surplus';
    }

    // Macros
    updateMacroRing('protein', totals.protein, targets.protein, percentage.protein);
    updateMacroRing('carbs', totals.carbs, targets.carbs, percentage.carbs);
    updateMacroRing('fats', totals.fats, targets.fats, percentage.fats);
}

function updateMacroRing(macro, value, target, percentage) {
    const ringEl = $(`#${macro}Ring`);
    const fillPath = ringEl.querySelector('.ring-fill');
    const percentEl = ringEl.querySelector('.macro-percent');
    const valueEl = $(`#${macro}Value`);

    const pct = Math.min(percentage, 100);
    fillPath.setAttribute('stroke-dasharray', `${pct}, 100`);
    percentEl.textContent = `${Math.round(percentage)}%`;
    valueEl.textContent = `${Math.round(value)}g / ${target}g`;
}

function updateMealsList(singleMeals, multiMeals = []) {
    const container = $('#mealsList');
    const hasMeals = (singleMeals && singleMeals.length > 0) || (multiMeals && multiMeals.length > 0);

    if (!hasMeals) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🍽️</div>
                <p class="empty-state-text">No meals logged yet today.<br>Tap + to add your first meal!</p>
            </div>
        `;
        return;
    }

    // Group all meals by meal type
    const grouped = {};
    const mealOrder = ['breakfast', 'lunch', 'dinner', 'snack'];

    // Add single-food meals
    if (singleMeals) {
        singleMeals.forEach(meal => {
            if (!grouped[meal.meal_type]) {
                grouped[meal.meal_type] = [];
            }
            grouped[meal.meal_type].push({ ...meal, type: 'single' });
        });
    }

    // Add multi-ingredient meals
    if (multiMeals) {
        multiMeals.forEach(meal => {
            if (!grouped[meal.meal_type]) {
                grouped[meal.meal_type] = [];
            }
            grouped[meal.meal_type].push({ ...meal, type: 'multi' });
        });
    }

    let html = '';
    mealOrder.forEach(type => {
        if (grouped[type] && grouped[type].length > 0) {
            const items = grouped[type].map(meal => {
                if (meal.type === 'multi') {
                    return createMultiMealCard(meal);
                } else {
                    return createMealItem(meal);
                }
            }).join('');

            html += `
                <div class="meal-group">
                    <div class="meal-group-header">${type.charAt(0).toUpperCase() + type.slice(1)}</div>
                    ${items}
                </div>
            `;
        }
    });

    container.innerHTML = html;

    // Add delete handlers for single meals
    container.querySelectorAll('.meal-delete').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const logId = btn.dataset.logId;
            if (confirm('Delete this meal?')) {
                try {
                    await API.delete(`/meals/${logId}`);
                    showToast('Meal deleted');
                    loadDashboard();
                } catch (error) {
                    showToast('Failed to delete meal');
                }
            }
        });
    });

    // Add expand/collapse handlers for multi-meals
    container.querySelectorAll('.multi-meal-header').forEach(header => {
        header.addEventListener('click', () => {
            const card = header.closest('.multi-meal-card');
            card.classList.toggle('expanded');
        });
    });

    // Add delete handlers for multi-meals
    container.querySelectorAll('.multi-meal-delete').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const mealId = btn.dataset.mealId;
            if (confirm('Delete this meal?')) {
                try {
                    await API.delete(`/meals/multi/${mealId}`);
                    showToast('Meal deleted');
                    loadDashboard();
                } catch (error) {
                    showToast('Failed to delete meal');
                }
            }
        });
    });
}

function createMealItem(meal) {
    const calories = Math.round(meal.calories * meal.portions);
    const protein = Math.round(meal.protein * meal.portions);
    const carbs = Math.round(meal.carbs * meal.portions);
    const fats = Math.round(meal.fats * meal.portions);

    return `
        <div class="meal-item">
            <div class="meal-info">
                <div class="meal-name">${meal.name}</div>
                <div class="meal-details">${meal.portions}x · P:${protein}g C:${carbs}g F:${fats}g</div>
            </div>
            <div class="meal-calories">${calories} cal</div>
            <button class="meal-delete" data-log-id="${meal.log_id}">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            </button>
        </div>
    `;
}

function createMultiMealCard(meal) {
    const calories = Math.round(meal.total_calories);
    const protein = Math.round(meal.total_protein);
    const carbs = Math.round(meal.total_carbs);
    const fats = Math.round(meal.total_fats);
    const ingredientCount = meal.ingredients ? meal.ingredients.length : 0;

    const ingredientsHtml = meal.ingredients ? meal.ingredients.map(ing => `
        <div class="mini-ingredient">
            <span class="mini-ingredient-name">${ing.food_name}</span>
            <span class="mini-ingredient-amount">${Math.round(ing.amount_grams)}g · ${Math.round(ing.calories)} cal</span>
        </div>
    `).join('') : '';

    return `
        <div class="multi-meal-card">
            <div class="multi-meal-header">
                <div class="multi-meal-icon">🍽️</div>
                <div class="multi-meal-info">
                    <div class="multi-meal-name">${meal.name}</div>
                    <div class="multi-meal-meta">${ingredientCount} ingredients</div>
                </div>
                <div class="multi-meal-calories">${calories} cal</div>
                <div class="multi-meal-expand">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                </div>
            </div>
            <div class="multi-meal-details">
                <div class="multi-meal-ingredients">
                    ${ingredientsHtml}
                </div>
                <div class="multi-meal-macros">
                    <span>P: ${protein}g</span>
                    <span>C: ${carbs}g</span>
                    <span>F: ${fats}g</span>
                </div>
                <div class="multi-meal-actions">
                    <button class="btn btn-secondary multi-meal-delete" data-meal-id="${meal.id}">Delete</button>
                </div>
            </div>
        </div>
    `;
}

function updateOffDayBanner(offDay) {
    const banner = $('#offDayBanner');
    if (offDay) {
        banner.classList.remove('hidden');
        banner.querySelector('.off-day-text').textContent = `Off Day - ${offDay.reason}`;
    } else {
        banner.classList.add('hidden');
    }
}

// ============================================
// Date Navigation
// ============================================

function changeDate(delta) {
    state.currentDate.setDate(state.currentDate.getDate() + delta);
    loadDashboard();
}

// ============================================
// Log Meal
// ============================================

async function openLogMealModal() {
    // Reset to quick mode by default
    state.mealMode = 'quick';
    updateMealModeUI();
    openModal('logMealModal');
    await loadMealFoodResults('recent');
}

function updateMealModeUI() {
    $$('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === state.mealMode);
    });

    const quickSection = $('#quickAddSection');
    const multiSection = $('#multiIngredientSection');

    if (state.mealMode === 'quick') {
        quickSection.classList.remove('hidden');
        multiSection.classList.add('hidden');
    } else {
        quickSection.classList.add('hidden');
        multiSection.classList.remove('hidden');
    }
}

async function loadMealFoodResults(source) {
    const container = $('#mealFoodResults');
    container.innerHTML = '<div class="empty-state"><div class="ptr-spinner"></div></div>';

    try {
        let foods;
        if (source === 'recent') {
            const data = await API.get('/foods/recent?limit=10');
            foods = data.foods;
        } else if (source === 'favorites') {
            const data = await API.get('/foods/favorites');
            foods = data.foods;
        } else {
            const data = await API.get(`/foods?q=${encodeURIComponent(source)}`);
            foods = data.foods;
        }

        if (foods.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p class="empty-state-text">No foods found</p>
                </div>
            `;
            return;
        }

        container.innerHTML = foods.map(food => `
            <div class="food-result-item" data-food-id="${food.id}">
                <div class="food-info">
                    <div class="food-name">${food.name}</div>
                    <div class="food-macros">P:${food.protein}g · C:${food.carbs}g · F:${food.fats}g</div>
                </div>
                <div class="food-calories">${food.calories} cal</div>
            </div>
        `).join('');

        // Add click handlers
        container.querySelectorAll('.food-result-item').forEach(item => {
            item.addEventListener('click', () => {
                const foodId = parseInt(item.dataset.foodId);
                selectFoodForMeal(foods.find(f => f.id === foodId));
            });
        });
    } catch (error) {
        container.innerHTML = '<div class="empty-state"><p class="empty-state-text">Failed to load foods</p></div>';
    }
}

function selectFoodForMeal(food) {
    state.selectedFood = food;

    closeModal('logMealModal');
    openModal('foodDetailsModal');

    $('#selectedFoodName').textContent = food.name;
    $('#selectedFoodInfo').innerHTML = `
        <div class="calc-row">
            <span class="calc-label">Serving Size</span>
            <span class="calc-value">${food.serving_size}</span>
        </div>
    `;

    $('#portionInput').value = 1;
    updateCalculatedNutrition();

    // Reset meal type selection
    $$('.meal-type-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.type === 'lunch');
    });
}

function updateCalculatedNutrition() {
    const food = state.selectedFood;
    if (!food) return;

    const portions = parseFloat($('#portionInput').value) || 1;
    const calories = Math.round(food.calories * portions);
    const protein = Math.round(food.protein * portions);
    const carbs = Math.round(food.carbs * portions);
    const fats = Math.round(food.fats * portions);

    $('#calculatedNutrition').innerHTML = `
        <div class="calc-row">
            <span class="calc-label">Calories</span>
            <span class="calc-value highlight">${calories}</span>
        </div>
        <div class="calc-row">
            <span class="calc-label">Protein</span>
            <span class="calc-value">${protein}g</span>
        </div>
        <div class="calc-row">
            <span class="calc-label">Carbs</span>
            <span class="calc-value">${carbs}g</span>
        </div>
        <div class="calc-row">
            <span class="calc-label">Fats</span>
            <span class="calc-value">${fats}g</span>
        </div>
    `;
}

async function confirmLogMeal() {
    const food = state.selectedFood;
    if (!food) return;

    const portions = parseFloat($('#portionInput').value) || 1;
    const mealType = $('.meal-type-btn.active').dataset.type;
    const dateStr = formatDate(state.currentDate, 'api');

    try {
        await API.post('/meals', {
            food_id: food.id,
            portions: portions,
            meal_type: mealType,
            date: dateStr
        });

        closeAllModals();
        showToast(`Logged ${portions}x ${food.name}`);
        loadDashboard();
    } catch (error) {
        showToast('Failed to log meal');
    }
}

// ============================================
// Multi-Ingredient Meal Builder
// ============================================

function openMultiMealBuilder() {
    // Reset multi-meal state
    state.multiMealIngredients = [];
    state.selectedIngredientFood = null;

    closeModal('logMealModal');
    openModal('multiMealModal');

    // Reset form
    $('#multiMealName').value = '';
    $$('#multiMealTypeSelector .meal-type-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.type === 'lunch');
    });

    updateIngredientsList();
    updateMealTotals();
}

function updateIngredientsList() {
    const container = $('#ingredientsList');
    const noIngredientsMsg = $('#noIngredientsMsg');
    const confirmBtn = $('#confirmMultiMeal');

    if (state.multiMealIngredients.length === 0) {
        container.innerHTML = `
            <div class="empty-state" id="noIngredientsMsg">
                <p class="empty-state-text">No ingredients added yet.<br>Tap "+ Add" to search and add foods.</p>
            </div>
        `;
        confirmBtn.disabled = true;
        return;
    }

    confirmBtn.disabled = false;

    container.innerHTML = state.multiMealIngredients.map((ing, index) => `
        <div class="ingredient-item" data-index="${index}">
            <div class="ingredient-info">
                <div class="ingredient-name">${ing.food.name}</div>
                <div class="ingredient-amount">${ing.amount_grams}g · P:${Math.round(ing.protein)}g C:${Math.round(ing.carbs)}g F:${Math.round(ing.fats)}g</div>
            </div>
            <div class="ingredient-calories">${Math.round(ing.calories)} cal</div>
            <button class="ingredient-remove" data-index="${index}">×</button>
        </div>
    `).join('');

    // Add remove handlers
    container.querySelectorAll('.ingredient-remove').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const index = parseInt(btn.dataset.index);
            removeIngredient(index);
        });
    });
}

function updateMealTotals() {
    let totalCalories = 0;
    let totalProtein = 0;
    let totalCarbs = 0;
    let totalFats = 0;

    state.multiMealIngredients.forEach(ing => {
        totalCalories += ing.calories;
        totalProtein += ing.protein;
        totalCarbs += ing.carbs;
        totalFats += ing.fats;
    });

    $('#totalCalories').textContent = Math.round(totalCalories);
    $('#totalProtein').textContent = `${Math.round(totalProtein)}g`;
    $('#totalCarbs').textContent = `${Math.round(totalCarbs)}g`;
    $('#totalFats').textContent = `${Math.round(totalFats)}g`;
}

function openAddIngredientModal() {
    openModal('addIngredientModal');
    $('#ingredientSearch').value = '';
    $('#ingredientSearchResults').innerHTML = '';

    // Load recent foods by default
    loadIngredientSearchResults('');
}

async function loadIngredientSearchResults(query) {
    const container = $('#ingredientSearchResults');
    container.innerHTML = '<div class="empty-state"><div class="ptr-spinner"></div></div>';

    try {
        let endpoint = query ? `/foods?q=${encodeURIComponent(query)}` : '/foods?limit=30';
        const data = await API.get(endpoint);
        const foods = data.foods;

        if (foods.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p class="empty-state-text">No foods found</p>
                </div>
            `;
            return;
        }

        container.innerHTML = foods.map(food => `
            <div class="food-result-item" data-food-id="${food.id}">
                <div class="food-info">
                    <div class="food-name">${food.name}</div>
                    <div class="food-macros">P:${food.protein}g · C:${food.carbs}g · F:${food.fats}g (per 100g)</div>
                </div>
                <div class="food-calories">${food.calories} cal</div>
            </div>
        `).join('');

        // Add click handlers
        container.querySelectorAll('.food-result-item').forEach(item => {
            item.addEventListener('click', () => {
                const foodId = parseInt(item.dataset.foodId);
                selectIngredientFood(foods.find(f => f.id === foodId));
            });
        });
    } catch (error) {
        container.innerHTML = '<div class="empty-state"><p class="empty-state-text">Failed to load foods</p></div>';
    }
}

function selectIngredientFood(food) {
    state.selectedIngredientFood = food;

    closeModal('addIngredientModal');
    openModal('ingredientAmountModal');

    $('#ingredientFoodName').textContent = food.name;
    $('#ingredientFoodInfo').innerHTML = `
        <div class="calc-row">
            <span class="calc-label">Per 100g</span>
            <span class="calc-value">${food.calories} cal</span>
        </div>
        <div class="calc-row">
            <span class="calc-label">Protein</span>
            <span class="calc-value">${food.protein}g</span>
        </div>
        <div class="calc-row">
            <span class="calc-label">Carbs</span>
            <span class="calc-value">${food.carbs}g</span>
        </div>
        <div class="calc-row">
            <span class="calc-label">Fats</span>
            <span class="calc-value">${food.fats}g</span>
        </div>
    `;

    $('#ingredientGrams').value = 100;
    updateIngredientNutrition();

    // Reset quick amount buttons
    $$('.quick-amount-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.grams === '100');
    });
}

function updateQuickAmountButtons(grams) {
    $$('.quick-amount-btn').forEach(btn => {
        btn.classList.toggle('active', parseInt(btn.dataset.grams) === grams);
    });
}

function updateIngredientNutrition() {
    const food = state.selectedIngredientFood;
    if (!food) return;

    const grams = parseFloat($('#ingredientGrams').value) || 100;
    const multiplier = grams / 100;

    const calories = Math.round(food.calories * multiplier);
    const protein = Math.round(food.protein * multiplier * 10) / 10;
    const carbs = Math.round(food.carbs * multiplier * 10) / 10;
    const fats = Math.round(food.fats * multiplier * 10) / 10;

    $('#ingredientNutrition').innerHTML = `
        <div class="calc-row">
            <span class="calc-label">Calories</span>
            <span class="calc-value highlight">${calories}</span>
        </div>
        <div class="calc-row">
            <span class="calc-label">Protein</span>
            <span class="calc-value">${protein}g</span>
        </div>
        <div class="calc-row">
            <span class="calc-label">Carbs</span>
            <span class="calc-value">${carbs}g</span>
        </div>
        <div class="calc-row">
            <span class="calc-label">Fats</span>
            <span class="calc-value">${fats}g</span>
        </div>
    `;
}

function addIngredientToMeal() {
    const food = state.selectedIngredientFood;
    if (!food) return;

    const grams = parseFloat($('#ingredientGrams').value) || 100;
    const multiplier = grams / 100;

    const ingredient = {
        food: food,
        amount_grams: grams,
        calories: food.calories * multiplier,
        protein: food.protein * multiplier,
        carbs: food.carbs * multiplier,
        fats: food.fats * multiplier
    };

    state.multiMealIngredients.push(ingredient);

    closeModal('ingredientAmountModal');
    openModal('multiMealModal');

    updateIngredientsList();
    updateMealTotals();

    showToast(`Added ${food.name}`);
}

function removeIngredient(index) {
    state.multiMealIngredients.splice(index, 1);
    updateIngredientsList();
    updateMealTotals();
}

async function confirmMultiMeal() {
    if (state.multiMealIngredients.length === 0) {
        showToast('Add at least one ingredient');
        return;
    }

    const mealName = $('#multiMealName').value.trim();
    const mealType = $('#multiMealTypeSelector .meal-type-btn.active').dataset.type;
    const dateStr = formatDate(state.currentDate, 'api');

    const ingredients = state.multiMealIngredients.map(ing => ({
        food_id: ing.food.id,
        amount_grams: ing.amount_grams
    }));

    try {
        await API.post('/meals/multi', {
            name: mealName,
            meal_type: mealType,
            ingredients: ingredients,
            date: dateStr
        });

        closeAllModals();
        showToast('Meal logged!');
        loadDashboard();

        // Reset state
        state.multiMealIngredients = [];
    } catch (error) {
        showToast('Failed to log meal');
        console.error(error);
    }
}

// ============================================
// Foods Management
// ============================================

async function loadFoods() {
    const container = $('#foodsList');
    container.innerHTML = '<div class="empty-state"><div class="ptr-spinner"></div></div>';

    try {
        let endpoint;
        if (state.foodsTab === 'favorites') {
            endpoint = '/foods/favorites';
        } else if (state.foodsTab === 'recent') {
            endpoint = '/foods/recent?limit=20';
        } else {
            endpoint = '/foods?limit=50';
        }

        const data = await API.get(endpoint);
        const foods = data.foods;

        if (foods.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🍎</div>
                    <p class="empty-state-text">No foods found.<br>Add your first food!</p>
                </div>
            `;
            return;
        }

        container.innerHTML = foods.map(food => createFoodItem(food)).join('');

        // Add event handlers
        container.querySelectorAll('.food-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.food-favorite')) {
                    const foodId = parseInt(item.dataset.foodId);
                    editFood(foods.find(f => f.id === foodId));
                }
            });
        });

        container.querySelectorAll('.food-favorite').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const foodId = parseInt(btn.dataset.foodId);
                try {
                    const result = await API.post(`/foods/${foodId}/favorite`);
                    btn.classList.toggle('active', result.is_favorite);
                    showToast(result.is_favorite ? 'Added to favorites' : 'Removed from favorites');
                } catch (error) {
                    showToast('Failed to update favorite');
                }
            });
        });
    } catch (error) {
        container.innerHTML = '<div class="empty-state"><p class="empty-state-text">Failed to load foods</p></div>';
    }
}

function createFoodItem(food) {
    return `
        <div class="food-item" data-food-id="${food.id}">
            <button class="food-favorite ${food.is_favorite ? 'active' : ''}" data-food-id="${food.id}">
                ${food.is_favorite ? '★' : '☆'}
            </button>
            <div class="food-info">
                <div class="food-name">${food.name}</div>
                <div class="food-macros">P:${food.protein}g · C:${food.carbs}g · F:${food.fats}g</div>
            </div>
            <div>
                <div class="food-calories">${food.calories} cal</div>
                <div class="food-serving">${food.serving_size}</div>
            </div>
        </div>
    `;
}

async function searchFoods(query) {
    if (!query) {
        loadFoods();
        return;
    }

    const container = $('#foodsList');
    container.innerHTML = '<div class="empty-state"><div class="ptr-spinner"></div></div>';

    try {
        const data = await API.get(`/foods?q=${encodeURIComponent(query)}`);
        const foods = data.foods;

        if (foods.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p class="empty-state-text">No foods matching "${query}"</p>
                </div>
            `;
            return;
        }

        container.innerHTML = foods.map(food => createFoodItem(food)).join('');

        // Re-add event handlers
        container.querySelectorAll('.food-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.food-favorite')) {
                    const foodId = parseInt(item.dataset.foodId);
                    editFood(foods.find(f => f.id === foodId));
                }
            });
        });
    } catch (error) {
        container.innerHTML = '<div class="empty-state"><p class="empty-state-text">Search failed</p></div>';
    }
}

function openAddFoodModal() {
    state.selectedFood = null;
    $('#foodModalTitle').textContent = 'Add Food';
    $('#foodName').value = '';
    $('#foodCalories').value = '';
    $('#foodProtein').value = '';
    $('#foodCarbs').value = '';
    $('#foodFats').value = '';
    $('#foodServing').value = '';
    $('#foodFavorite').checked = false;
    openModal('addFoodModal');
}

function editFood(food) {
    state.selectedFood = food;
    $('#foodModalTitle').textContent = 'Edit Food';
    $('#foodName').value = food.name;
    $('#foodCalories').value = food.calories;
    $('#foodProtein').value = food.protein;
    $('#foodCarbs').value = food.carbs;
    $('#foodFats').value = food.fats;
    $('#foodServing').value = food.serving_size;
    $('#foodFavorite').checked = food.is_favorite;
    openModal('addFoodModal');
}

async function saveFood() {
    const foodData = {
        name: $('#foodName').value.trim(),
        calories: parseFloat($('#foodCalories').value) || 0,
        protein: parseFloat($('#foodProtein').value) || 0,
        carbs: parseFloat($('#foodCarbs').value) || 0,
        fats: parseFloat($('#foodFats').value) || 0,
        serving_size: $('#foodServing').value.trim() || '1 serving'
    };

    if (!foodData.name) {
        showToast('Food name is required');
        return;
    }

    try {
        if (state.selectedFood) {
            await API.put(`/foods/${state.selectedFood.id}`, foodData);
            showToast('Food updated');
        } else {
            const result = await API.post('/foods', foodData);
            if ($('#foodFavorite').checked) {
                await API.post(`/foods/${result.food.id}/favorite`);
            }
            showToast('Food added');
        }

        closeModal('addFoodModal');
        loadFoods();
    } catch (error) {
        showToast('Failed to save food');
    }
}

// ============================================
// Analytics
// ============================================

async function loadAnalytics() {
    try {
        const data = await API.get('/analytics/breakdown?weeks=4&months=3');
        updateAnalyticsSummary(data);
        updateAnalyticsChart(data);
        updateBreakdownList(data);
    } catch (error) {
        showToast('Failed to load analytics');
    }
}

function updateAnalyticsSummary(data) {
    const container = $('#analyticsSummary');
    const currentWeek = data.weeks[0];
    const currentMonth = data.months[0];

    container.innerHTML = `
        <div class="summary-card">
            <div class="summary-value">${Math.round(currentWeek.averages.calories)}</div>
            <div class="summary-label">Weekly Avg Cal</div>
        </div>
        <div class="summary-card">
            <div class="summary-value">${Math.round(currentMonth.averages.calories)}</div>
            <div class="summary-label">Monthly Avg Cal</div>
        </div>
        <div class="summary-card">
            <div class="summary-value">${currentWeek.tracked_days}</div>
            <div class="summary-label">Days Tracked</div>
        </div>
        <div class="summary-card">
            <div class="summary-value">${currentWeek.off_day_count}</div>
            <div class="summary-label">Off Days</div>
        </div>
    `;
}

function updateAnalyticsChart(data) {
    const ctx = $('#analyticsChart').getContext('2d');

    if (state.chart) {
        state.chart.destroy();
    }

    const isWeekly = state.analyticsTab === 'weekly';
    const items = isWeekly ? data.weeks : data.months;

    const labels = items.map(item => {
        if (isWeekly) {
            const start = new Date(item.week_start);
            return start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        } else {
            return item.month_name;
        }
    }).reverse();

    const calorieData = items.map(item => Math.round(item.averages.calories)).reverse();
    const proteinData = items.map(item => Math.round(item.averages.protein)).reverse();

    state.chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Avg Calories',
                    data: calorieData,
                    backgroundColor: 'rgba(79, 70, 229, 0.8)',
                    borderRadius: 8
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        display: false
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function updateBreakdownList(data) {
    const container = $('#breakdownList');
    const isWeekly = state.analyticsTab === 'weekly';
    const items = isWeekly ? data.weeks : data.months;

    container.innerHTML = items.map(item => {
        const dateLabel = isWeekly
            ? `${new Date(item.week_start).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${new Date(item.week_end).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`
            : item.month_name;

        return `
            <div class="breakdown-item">
                <div>
                    <div class="breakdown-date">${dateLabel}</div>
                    <div class="breakdown-details">
                        P: ${Math.round(item.averages.protein)}g ·
                        C: ${Math.round(item.averages.carbs)}g ·
                        F: ${Math.round(item.averages.fats)}g
                    </div>
                </div>
                <div class="breakdown-stats">
                    <div class="breakdown-calories">${Math.round(item.averages.calories)} cal/day</div>
                    ${item.off_day_count > 0 ? `<div class="breakdown-off-days">${item.off_day_count} off days</div>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// ============================================
// Settings
// ============================================

async function loadSettings() {
    try {
        const data = await API.get('/settings');
        state.settings = data.settings;

        // Update goal selector
        $$('.goal-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.goal === state.settings.goal_type);
        });

        // Update target inputs
        $('#calorieTarget').value = state.settings.daily_calorie_target || 2000;
        $('#proteinTarget').value = state.settings.protein_target || 150;
        $('#carbsTarget').value = state.settings.carbs_target || 200;
        $('#fatsTarget').value = state.settings.fats_target || 65;

        // Load weight history
        await loadWeightHistory();

        // Load off days
        await loadOffDays();
    } catch (error) {
        showToast('Failed to load settings');
    }
}

async function saveGoal(goalType) {
    try {
        await API.put('/settings/goal', { goal_type: goalType });
        $$('.goal-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.goal === goalType);
        });
        showToast('Goal updated');
    } catch (error) {
        showToast('Failed to update goal');
    }
}

async function saveTargets() {
    const settings = {
        daily_calorie_target: $('#calorieTarget').value,
        protein_target: $('#proteinTarget').value,
        carbs_target: $('#carbsTarget').value,
        fats_target: $('#fatsTarget').value
    };

    try {
        await API.put('/settings', settings);
        showToast('Targets saved');
    } catch (error) {
        showToast('Failed to save targets');
    }
}

async function loadWeightHistory() {
    try {
        const data = await API.get('/weight?limit=10');
        const container = $('#weightHistory');

        if (data.history.length === 0) {
            container.innerHTML = '<p class="empty-state-text">No weight entries yet</p>';
            return;
        }

        container.innerHTML = data.history.map((entry, index) => {
            const prevWeight = data.history[index + 1]?.weight;
            let changeHtml = '';
            if (prevWeight !== undefined) {
                const change = entry.weight - prevWeight;
                if (change !== 0) {
                    const direction = change > 0 ? 'up' : 'down';
                    changeHtml = `<span class="weight-change ${direction}">${change > 0 ? '+' : ''}${change.toFixed(1)}</span>`;
                }
            }

            return `
                <div class="weight-entry">
                    <div>
                        <span class="weight-value">${entry.weight} lbs</span>
                        ${changeHtml}
                    </div>
                    <span class="weight-date">${entry.recorded_at}</span>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to load weight history:', error);
    }
}

async function logWeight() {
    const weight = parseFloat($('#weightInput').value);
    if (!weight || weight <= 0) {
        showToast('Please enter a valid weight');
        return;
    }

    try {
        await API.post('/weight', { weight });
        $('#weightInput').value = '';
        showToast('Weight logged');
        loadWeightHistory();
    } catch (error) {
        showToast('Failed to log weight');
    }
}

// ============================================
// Off Days
// ============================================

async function loadOffDays() {
    try {
        const data = await API.get('/off-days');
        const container = $('#offDaysList');

        if (data.off_days.length === 0) {
            container.innerHTML = '<p class="empty-state-text">No off days this month</p>';
            return;
        }

        container.innerHTML = data.off_days.map(offDay => `
            <div class="off-day-item">
                <div class="off-day-info">
                    <span class="off-day-date">${offDay.date}</span>
                    <span class="off-day-reason">${offDay.reason}</span>
                </div>
                <button class="icon-btn" onclick="removeOffDay('${offDay.date}')">×</button>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load off days:', error);
    }
}

function openOffDayModal() {
    openModal('offDayModal');
    $$('.reason-btn').forEach(btn => btn.classList.remove('active'));
    $('#otherReasonGroup').classList.add('hidden');
}

async function confirmOffDay() {
    const selectedReason = $('.reason-btn.active');
    if (!selectedReason) {
        showToast('Please select a reason');
        return;
    }

    let reason = selectedReason.dataset.reason;
    if (reason === 'other') {
        reason = $('#otherReason').value.trim() || 'other';
    }

    try {
        const dateStr = formatDate(state.currentDate, 'api');
        await API.post('/off-days', {
            date: dateStr,
            reason: reason
        });

        closeModal('offDayModal');
        showToast('Marked as off day');
        loadDashboard();
        loadOffDays();
    } catch (error) {
        showToast('Failed to mark off day');
    }
}

async function removeOffDay(dateStr) {
    try {
        await API.delete(`/off-days/${dateStr}`);
        showToast('Off day removed');
        loadDashboard();
        loadOffDays();
    } catch (error) {
        showToast('Failed to remove off day');
    }
}

// ============================================
// Data Export/Import
// ============================================

async function exportData() {
    try {
        const data = await API.get('/export');
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `food_tracker_backup_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast('Data exported');
    } catch (error) {
        showToast('Failed to export data');
    }
}

function triggerImport() {
    $('#importFile').click();
}

async function importData(event) {
    const file = event.target.files[0];
    if (!file) return;

    try {
        const text = await file.text();
        const data = JSON.parse(text);

        if (!confirm('This will merge the imported data with your existing data. Continue?')) {
            return;
        }

        await API.post('/import?merge=true', data);
        showToast('Data imported successfully');
        loadDashboard();
        loadFoods();
        loadSettings();
    } catch (error) {
        showToast('Failed to import data');
    }

    event.target.value = '';
}

// ============================================
// Dark Mode
// ============================================

function initDarkMode() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        document.documentElement.setAttribute('data-theme', 'dark');
        $('#darkModeToggle').checked = true;
    }
}

function toggleDarkMode() {
    const isDark = $('#darkModeToggle').checked;
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

// ============================================
// Pull to Refresh
// ============================================

let touchStartY = 0;
let touchEndY = 0;

function initPullToRefresh() {
    const mainContent = $('#mainContent');
    const pullIndicator = $('#pullRefresh');

    mainContent.addEventListener('touchstart', (e) => {
        touchStartY = e.touches[0].clientY;
    }, { passive: true });

    mainContent.addEventListener('touchmove', (e) => {
        touchEndY = e.touches[0].clientY;
        const diff = touchEndY - touchStartY;

        if (mainContent.scrollTop === 0 && diff > 50) {
            pullIndicator.classList.add('visible');
        }
    }, { passive: true });

    mainContent.addEventListener('touchend', () => {
        const diff = touchEndY - touchStartY;

        if (mainContent.scrollTop === 0 && diff > 100) {
            pullIndicator.classList.add('visible');
            loadDashboard().then(() => {
                setTimeout(() => {
                    pullIndicator.classList.remove('visible');
                }, 500);
            });
        } else {
            pullIndicator.classList.remove('visible');
        }

        touchStartY = 0;
        touchEndY = 0;
    }, { passive: true });
}

// ============================================
// Service Worker Registration
// ============================================

async function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        try {
            await navigator.serviceWorker.register('/sw.js');
            console.log('Service Worker registered');
        } catch (error) {
            console.log('Service Worker registration failed:', error);
        }
    }
}

// ============================================
// Event Listeners
// ============================================

function initEventListeners() {
    // Navigation
    $$('.nav-item[data-view]').forEach(item => {
        item.addEventListener('click', () => switchView(item.dataset.view));
    });

    // Quick Add Button
    $('#quickAddBtn').addEventListener('click', openLogMealModal);
    $('#floatingFab')?.addEventListener('click', openLogMealModal);

    // Settings button
    $('#settingsBtn').addEventListener('click', () => switchView('settings'));

    // Date navigation
    $('#prevDay').addEventListener('click', () => changeDate(-1));
    $('#nextDay').addEventListener('click', () => changeDate(1));
    $('#currentDate').addEventListener('click', () => {
        state.currentDate = new Date();
        loadDashboard();
    });

    // Modal close buttons
    $$('[data-close]').forEach(btn => {
        btn.addEventListener('click', () => closeModal(btn.dataset.close));
    });

    // Modal overlay click
    $('#modalOverlay').addEventListener('click', closeAllModals);

    // Log Meal Modal
    $('#mealFoodSearch').addEventListener('input', debounce((e) => {
        const query = e.target.value.trim();
        if (query) {
            loadMealFoodResults(query);
        } else {
            loadMealFoodResults('recent');
        }
    }, 300));

    $$('.quick-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            $$('.quick-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadMealFoodResults(btn.dataset.source);
        });
    });

    // Food Details Modal
    $('#decreasePortion').addEventListener('click', () => {
        const input = $('#portionInput');
        const value = Math.max(0.1, parseFloat(input.value) - 0.5);
        input.value = value.toFixed(1);
        updateCalculatedNutrition();
    });

    $('#increasePortion').addEventListener('click', () => {
        const input = $('#portionInput');
        const value = parseFloat(input.value) + 0.5;
        input.value = value.toFixed(1);
        updateCalculatedNutrition();
    });

    $('#portionInput').addEventListener('input', updateCalculatedNutrition);

    $$('.meal-type-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            $$('.meal-type-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    $('#confirmLogMeal').addEventListener('click', confirmLogMeal);

    // Meal Mode Selector
    $$('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            state.mealMode = btn.dataset.mode;
            updateMealModeUI();
        });
    });

    // Start Multi-Meal Builder
    $('#startMultiMeal').addEventListener('click', openMultiMealBuilder);

    // Multi-Meal Type Selector
    $$('#multiMealTypeSelector .meal-type-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            $$('#multiMealTypeSelector .meal-type-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // Add Ingredient Button
    $('#addIngredientBtn').addEventListener('click', openAddIngredientModal);

    // Ingredient Search
    $('#ingredientSearch').addEventListener('input', debounce((e) => {
        loadIngredientSearchResults(e.target.value.trim());
    }, 300));

    // Ingredient Amount Controls
    $('#decreaseGrams').addEventListener('click', () => {
        const input = $('#ingredientGrams');
        const value = Math.max(10, parseInt(input.value) - 10);
        input.value = value;
        updateIngredientNutrition();
        updateQuickAmountButtons(value);
    });

    $('#increaseGrams').addEventListener('click', () => {
        const input = $('#ingredientGrams');
        const value = parseInt(input.value) + 10;
        input.value = value;
        updateIngredientNutrition();
        updateQuickAmountButtons(value);
    });

    $('#ingredientGrams').addEventListener('input', () => {
        updateIngredientNutrition();
        updateQuickAmountButtons(parseInt($('#ingredientGrams').value));
    });

    // Quick Amount Buttons
    $$('.quick-amount-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const grams = parseInt(btn.dataset.grams);
            $('#ingredientGrams').value = grams;
            updateIngredientNutrition();
            updateQuickAmountButtons(grams);
        });
    });

    // Confirm Add Ingredient
    $('#confirmAddIngredient').addEventListener('click', addIngredientToMeal);

    // Confirm Multi-Meal
    $('#confirmMultiMeal').addEventListener('click', confirmMultiMeal);

    // Foods View
    $('#foodSearch').addEventListener('input', debounce((e) => {
        searchFoods(e.target.value.trim());
    }, 300));

    $$('.foods-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            $$('.foods-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.foodsTab = btn.dataset.tab;
            loadFoods();
        });
    });

    $('#addFoodBtn').addEventListener('click', openAddFoodModal);
    $('#saveFoodBtn').addEventListener('click', saveFood);

    // Analytics tabs
    $$('.analytics-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            $$('.analytics-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.analyticsTab = btn.dataset.tab;
            loadAnalytics();
        });
    });

    // Settings
    $$('.goal-btn').forEach(btn => {
        btn.addEventListener('click', () => saveGoal(btn.dataset.goal));
    });

    $('#saveTargets').addEventListener('click', saveTargets);
    $('#logWeight').addEventListener('click', logWeight);
    $('#markOffDay').addEventListener('click', openOffDayModal);
    $('#darkModeToggle').addEventListener('change', toggleDarkMode);
    $('#exportData').addEventListener('click', exportData);
    $('#importData').addEventListener('click', triggerImport);
    $('#importFile').addEventListener('change', importData);

    // Off Day Modal
    $$('.reason-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            $$('.reason-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            $('#otherReasonGroup').classList.toggle('hidden', btn.dataset.reason !== 'other');
        });
    });

    $('#confirmOffDay').addEventListener('click', confirmOffDay);

    // Off Day Banner remove
    $('#removeOffDay').addEventListener('click', async () => {
        const dateStr = formatDate(state.currentDate, 'api');
        await removeOffDay(dateStr);
    });
}

// ============================================
// Initialize App
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initDarkMode();
    initEventListeners();
    initPullToRefresh();
    registerServiceWorker();
    loadDashboard();
});
