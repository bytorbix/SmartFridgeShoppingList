class SmartShoppingListWithTags {
  constructor() {
    this.shoppingList = []
    this.categories = []
    this.tagStats = []
    this.currentCategory = "all"
    this.currentFilter = "all"
    this.isRecording = false
    this.pollInterval = null
    this.lastModified = null
    this.microphoneAvailable = false

    // Voice recording properties
    this.mediaRecorder = null
    this.audioChunks = []
    this.recordingTimeout = null

    this.initializeElements()
    this.bindEvents()
    this.loadCategories()
    this.startPolling()
    this.loadShoppingList()
    this.checkMicrophonePermission()
  }

  initializeElements() {
    // Navigation elements
    this.floatingNavBtn = document.getElementById("floatingNavBtn")
    this.categoriesOverlay = document.getElementById("categoriesOverlay")
    this.categoriesSidebar = document.getElementById("categoriesSidebar")
    this.sidebarClose = document.getElementById("sidebarClose")
    this.categoriesList = document.getElementById("categoriesList")
    this.statsBtn = document.getElementById("statsBtn")

    // Voice elements
    this.voiceSection = document.querySelector(".voice-section")
    this.voiceButton = document.getElementById("voiceButton")
    this.voiceLabel = document.getElementById("voiceLabel")
    this.voiceFeedback = document.getElementById("voiceFeedback")
    this.voiceHint = document.querySelector(".voice-hint")

    // List elements
    this.shoppingListEl = document.getElementById("shoppingList")
    this.emptyState = document.getElementById("emptyState")
    this.syncStatus = document.getElementById("syncStatus")
    this.clearAllBtn = document.getElementById("clearAllBtn")
    this.listTitle = document.getElementById("listTitle")
    this.currentCategoryEl = document.getElementById("currentCategory")
    this.totalCount = document.getElementById("totalCount")

    // Filter elements
    this.filterToggle = document.getElementById("filterToggle")
    this.filterBar = document.getElementById("filterBar")

    // Modal elements
    this.addButton = document.getElementById("addButton")
    this.addModal = document.getElementById("addModal")
    this.closeModal = document.getElementById("closeModal")
    this.cancelBtn = document.getElementById("cancelBtn")
    this.saveBtn = document.getElementById("saveBtn")
    this.itemName = document.getElementById("itemName")
    this.itemQuantity = document.getElementById("itemQuantity")
    this.itemCategory = document.getElementById("itemCategory")

    // Stats modal elements
    this.statsModal = document.getElementById("statsModal")
    this.closeStatsModal = document.getElementById("closeStatsModal")
    this.statsContent = document.getElementById("statsContent")

    // Loading overlay
    this.loadingOverlay = document.getElementById("loadingOverlay")

    // Initially hide voice section until permission is checked
    this.hideVoiceSection()
  }

  bindEvents() {
    // Navigation events
    this.floatingNavBtn?.addEventListener("click", () => this.openCategories())
    this.sidebarClose?.addEventListener("click", () => this.closeCategories())
    this.categoriesOverlay?.addEventListener("click", (e) => {
      if (e.target === this.categoriesOverlay) {
        this.closeCategories()
      }
    })
    this.statsBtn?.addEventListener("click", () => {
      this.closeCategories()
      this.openStatsModal()
    })

    // Voice button - only bind if voice section is available
    this.voiceButton?.addEventListener("click", () => this.toggleVoiceRecording())

    // Add button and modal
    this.addButton?.addEventListener("click", () => this.openAddModal())
    this.closeModal?.addEventListener("click", () => this.closeAddModal())
    this.cancelBtn?.addEventListener("click", () => this.closeAddModal())
    this.saveBtn?.addEventListener("click", () => this.saveNewItem())

    // Stats modal
    this.closeStatsModal?.addEventListener("click", (e) => {
      e.preventDefault()
      e.stopPropagation()
      this.statsModal?.classList.remove("active")
    })

    // Filter toggle
    this.filterToggle?.addEventListener("click", () => this.toggleFilterBar())

    // Clear all button
    this.clearAllBtn?.addEventListener("click", () => this.clearAllItems())

    // Modal backdrop clicks
    this.addModal?.addEventListener("click", (e) => {
      if (e.target === this.addModal) {
        this.closeAddModal()
      }
    })

    this.statsModal?.addEventListener("click", (e) => {
      if (e.target === this.statsModal) {
        this.statsModal?.classList.remove("active")
      }
    })

    // Enter key in modal inputs
    this.itemName?.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        this.saveNewItem()
      }
    })

    this.itemQuantity?.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        this.saveNewItem()
      }
    })

    // Filter buttons
    document.addEventListener("click", (e) => {
      if (e.target.classList.contains("filter-btn")) {
        this.handleFilterChange(e.target.dataset.filter)
      }
    })
  }

  // ============================================================================
  // VOICE UI VISIBILITY MANAGEMENT
  // ============================================================================

  showVoiceSection() {
    if (this.voiceSection) {
      this.voiceSection.style.display = "block"
      this.voiceSection.style.opacity = "0"
      this.voiceSection.style.transform = "translateY(-20px)"

      // Animate in
      setTimeout(() => {
        this.voiceSection.style.transition = "all 0.3s ease"
        this.voiceSection.style.opacity = "1"
        this.voiceSection.style.transform = "translateY(0)"
      }, 50)

      console.log("Voice section is now visible")
    }
  }

  hideVoiceSection() {
    if (this.voiceSection) {
      this.voiceSection.style.display = "none"
      console.log("Voice section is hidden")
    }
  }

  updateEmptyStateText() {
    if (!this.emptyState) return

    const h3 = this.emptyState.querySelector("h3")
    const p = this.emptyState.querySelector("p")

    if (this.currentCategory !== "all") {
      if (h3) h3.textContent = `אין פריטים בקטגוריה "${this.currentCategory}"`
      if (p) p.textContent = "בחר קטגוריה אחרת או הוסף פריטים חדשים"
    } else {
      if (h3) h3.textContent = "הרשימה ריקה"
      if (this.microphoneAvailable) {
        if (p) p.textContent = "הוסף פריטים באמצעות הקול או לחץ על הוסף פריט"
      } else {
        if (p) p.textContent = "לחץ על הוסף פריט כדי להתחיל"
      }
    }
  }

  // ============================================================================
  // MICROPHONE PERMISSION & VOICE FUNCTIONALITY
  // ============================================================================

  async checkMicrophonePermission() {
    try {
      console.log("Checking microphone permission...")

      // Check if the browser supports getUserMedia
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.log("Browser doesn't support getUserMedia")
        this.updateVoiceStatus("not-supported")
        this.hideVoiceSection()
        this.updateEmptyStateText()
        return
      }

      // Try to access microphone
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      // If we get here, permission was granted
      stream.getTracks().forEach(track => track.stop()) // Clean up

      console.log("Microphone permission granted")
      this.microphoneAvailable = true
      this.updateVoiceStatus("ready")
      this.showVoiceSection()
      this.updateEmptyStateText()

    } catch (error) {
      console.error("Microphone permission denied or error:", error)
      this.microphoneAvailable = false

      if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        this.updateVoiceStatus("no-permission")
      } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
        this.updateVoiceStatus("no-device")
      } else {
        this.updateVoiceStatus("not-supported")
      }

      this.hideVoiceSection()
      this.updateEmptyStateText()
    }
  }

  updateVoiceStatus(status) {
    if (!this.voiceHint || !this.voiceButton) return

    switch (status) {
      case "ready":
        this.voiceHint.textContent = "הוסף פריטים בקול עם קטגוריזציה אוטומטית"
        this.voiceButton.disabled = false
        break
      case "no-permission":
        this.voiceHint.textContent = "יש צורך בהרשאה לגישה למיקרופון"
        this.voiceButton.disabled = true
        console.log("Microphone permission required")
        break
      case "no-device":
        this.voiceHint.textContent = "לא נמצא מיקרופון במכשיר"
        this.voiceButton.disabled = true
        console.log("No microphone device found")
        break
      case "not-supported":
        this.voiceHint.textContent = "הדפדפן לא תומך בהקלטה קולית"
        this.voiceButton.disabled = true
        console.log("Browser doesn't support voice recording")
        break
    }
  }

  toggleVoiceRecording() {
    if (!this.microphoneAvailable) {
      this.showNotification("גישה למיקרופון לא זמינה")
      return
    }

    if (this.isRecording) {
      this.stopVoiceRecording()
    } else {
      this.startVoiceRecording()
    }
  }

  async startVoiceRecording() {
    try {
      console.log("Starting voice recording...")

      // Double-check microphone access before recording
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        }
      })

      // Initialize MediaRecorder
      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })

      this.audioChunks = []

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data)
        }
      }

      this.mediaRecorder.onstop = async () => {
        console.log("Recording stopped, processing audio...")
        await this.processVoiceRecording()
        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop())
      }

      this.mediaRecorder.onerror = (event) => {
        console.error("MediaRecorder error:", event.error)
        this.showNotification("שגיאה בהקלטה: " + event.error)
        this.resetVoiceUI()
      }

      // Update UI
      this.isRecording = true
      this.voiceButton?.classList.add("recording")
      this.voiceFeedback?.classList.add("active")
      if (this.voiceLabel) {
        this.voiceLabel.textContent = "מקליט... (לחץ שוב לעצירה)"
      }

      // Start recording
      this.mediaRecorder.start(100) // Collect data every 100ms

      // Auto-stop after 10 seconds
      this.recordingTimeout = setTimeout(() => {
        if (this.isRecording) {
          console.log("Auto-stopping recording after 10 seconds")
          this.stopVoiceRecording()
        }
      }, 10000)

    } catch (error) {
      console.error("Error starting voice recording:", error)

      if (error.name === 'NotAllowedError') {
        this.showNotification("יש צורך בהרשאה לגישה למיקרופון")
        this.microphoneAvailable = false
        this.hideVoiceSection()
      } else {
        this.showNotification("שגיאה בהפעלת ההקלטה: " + error.message)
      }

      this.resetVoiceUI()
    }
  }

  stopVoiceRecording() {
    if (this.mediaRecorder && this.isRecording) {
      console.log("Stopping voice recording...")
      this.mediaRecorder.stop()
      this.isRecording = false

      // Clear timeout
      if (this.recordingTimeout) {
        clearTimeout(this.recordingTimeout)
        this.recordingTimeout = null
      }

      // Update UI
      this.voiceButton?.classList.remove("recording")
      this.voiceFeedback?.classList.remove("active")
      if (this.voiceLabel) {
        this.voiceLabel.textContent = "מעבד הקלטה..."
      }
    }
  }

  async processVoiceRecording() {
    try {
      if (this.audioChunks.length === 0) {
        this.showNotification("לא נקלט קול")
        this.resetVoiceUI()
        return
      }

      console.log(`Processing ${this.audioChunks.length} audio chunks`)

      // Create audio blob
      const audioBlob = new Blob(this.audioChunks, { type: "audio/webm" })
      console.log(`Audio blob size: ${audioBlob.size} bytes`)

      if (audioBlob.size === 0) {
        this.showNotification("לא נקלט קול")
        this.resetVoiceUI()
        return
      }

      // Prepare form data
      const formData = new FormData()
      formData.append("file", audioBlob, "voice_command.webm")

      // Update UI
      this.updateSyncStatus("syncing")
      if (this.voiceLabel) {
        this.voiceLabel.textContent = "מעבד פקודה קולית..."
      }

      console.log("Sending audio to server...")

      // Send to voice command endpoint
      const response = await fetch("/api/voice-command", {
        method: "POST",
        body: formData,
      })

      const result = await response.json()
      console.log("Voice command result:", result)

      if (result.success) {
        // Show what was heard
        this.showNotification(`שמעתי: "${result.transcription}"`)

        // Play TTS response
        if (result.audio_url) {
          console.log("Playing TTS response:", result.audio_url)
          await this.playAudioResponse(result.audio_url)
        }

        // Refresh the shopping list to show changes
        await this.loadShoppingList()
        this.updateSyncStatus("synced")

        // Show success message
        setTimeout(() => {
          this.showNotification("פקודה בוצעה בהצלחה!")
        }, 1000)

      } else {
        console.error("Voice command failed:", result.error)

        // Show error message
        this.showNotification(result.response || "לא הצלחתי לעבד את הפקודה")

        // Play error TTS if available
        if (result.audio_url) {
          await this.playAudioResponse(result.audio_url)
        }

        this.updateSyncStatus("error")
      }

    } catch (error) {
      console.error("Error processing voice recording:", error)
      this.updateSyncStatus("error")
      this.showNotification("שגיאה בעיבוד הפקודה הקולית")
    } finally {
      this.resetVoiceUI()
    }
  }

  async playAudioResponse(audioUrl) {
    try {
      console.log("Playing audio response:", audioUrl)
      const audio = new Audio(audioUrl)

      // Handle audio loading errors
      audio.onerror = (e) => {
        console.error("Audio playback error:", e)
        this.showNotification("שגיאה בהשמעת התגובה")
      }

      // Wait for audio to load
      await new Promise((resolve, reject) => {
        audio.onloadeddata = resolve
        audio.onerror = reject
        audio.load()
      })

      // Play audio
      await audio.play()
      console.log("Audio played successfully")

    } catch (error) {
      console.error("Error playing audio response:", error)
      this.showNotification("לא ניתן להשמיע תגובה קולית")
    }
  }

  resetVoiceUI() {
    this.isRecording = false
    this.voiceButton?.classList.remove("recording")
    this.voiceFeedback?.classList.remove("active")
    if (this.voiceLabel) {
      this.voiceLabel.textContent = "לחץ כדי לדבר"
    }
  }

  // ============================================================================
  // EXISTING FUNCTIONALITY (unchanged)
  // ============================================================================

  openCategories() {
    this.categoriesOverlay?.classList.add("active")
  }

  closeCategories() {
    this.categoriesOverlay?.classList.remove("active")
  }

  async loadCategories() {
    try {
      const response = await fetch("/api/tags")
      const data = await response.json()
      this.categories = data.tags || []
      this.renderCategories()
      this.populateCategorySelect()
    } catch (error) {
      console.error("Error loading categories:", error)
    }
  }

  renderCategories() {
    if (!this.categoriesList) return

    const categoryIcons = {
      "חלב ומוצרי חלב": "fas fa-glass-whiskey",
      "בשר ודגים": "fas fa-drumstick-bite",
      "ירקות": "fas fa-carrot",
      "פירות": "fas fa-apple-alt",
      "לחם ומאפים": "fas fa-bread-slice",
      "משקאות": "fas fa-coffee",
      "חטיפים וממתקים": "fas fa-candy-cane",
      "מוצרי בית": "fas fa-home",
      "קפואים": "fas fa-snowflake",
      "תבלינים ורטבים": "fas fa-pepper-hot",
      "דגנים וקטניות": "fas fa-seedling",
      "אחר": "fas fa-ellipsis-h"
    }

    // Create the "all" category at the top
    const allCategoryHtml = `
      <div class="category-item active" data-category="all">
        <i class="fas fa-list"></i>
        <span>כל הפריטים</span>
        <span class="count" id="totalCount">0</span>
      </div>
    `

    const categoriesHtml = this.categories
      .map(category => {
        const icon = categoryIcons[category] || "fas fa-tag"
        return `
          <div class="category-item" data-category="${category}">
            <i class="${icon}"></i>
            <span>${category}</span>
            <span class="count" id="count-${category}">0</span>
          </div>
        `
      })
      .join("")

    this.categoriesList.innerHTML = allCategoryHtml + categoriesHtml

    // Re-bind category click events
    this.categoriesList.addEventListener("click", (e) => {
      const categoryItem = e.target.closest(".category-item")
      if (categoryItem) {
        const category = categoryItem.dataset.category
        this.handleCategoryChange(category)
        this.closeCategories()
      }
    })

    // Update counts after rendering
    this.updateCategoryCounts()
  }

  populateCategorySelect() {
    if (!this.itemCategory) return

    this.itemCategory.innerHTML = this.categories
      .map(category => `<option value="${category}">${category}</option>`)
      .join("")
  }

  handleCategoryChange(category) {
    this.currentCategory = category
    this.updateCategorySelection()
    this.filterShoppingList()
    this.updateCurrentCategoryDisplay()
  }

  updateCategorySelection() {
    document.querySelectorAll(".category-item").forEach(item => {
      item.classList.remove("active")
    })

    const activeCategory = document.querySelector(`[data-category="${this.currentCategory}"]`)
    if (activeCategory) {
      activeCategory.classList.add("active")
    }
  }

  updateCurrentCategoryDisplay() {
    if (!this.currentCategoryEl) return

    const categoryName = this.currentCategory === "all" ? "כל הפריטים" : this.currentCategory
    this.currentCategoryEl.querySelector("span").textContent = categoryName
  }

  toggleFilterBar() {
    if (!this.filterBar) return
    this.filterBar.classList.toggle("active")
  }

  handleFilterChange(filter) {
    this.currentFilter = filter

    // Update filter buttons
    document.querySelectorAll(".filter-btn").forEach(btn => {
      btn.classList.remove("active")
    })

    const activeBtn = document.querySelector(`[data-filter="${filter}"]`)
    if (activeBtn) {
      activeBtn.classList.add("active")
    }

    this.filterShoppingList()
  }

  filterShoppingList() {
    const items = document.querySelectorAll(".shopping-item")

    items.forEach(item => {
      const itemCategory = item.dataset.category
      const itemCompleted = item.classList.contains("completed")

      let showItem = true

      // Category filter
      if (this.currentCategory !== "all" && itemCategory !== this.currentCategory) {
        showItem = false
      }

      // Status filter
      if (this.currentFilter === "pending" && itemCompleted) {
        showItem = false
      } else if (this.currentFilter === "completed" && !itemCompleted) {
        showItem = false
      }

      if (showItem) {
        item.classList.remove("hidden")
      } else {
        item.classList.add("hidden")
      }
    })

    this.updateEmptyState()
  }

  updateEmptyState() {
    if (!this.shoppingListEl || !this.emptyState) return

    const visibleItems = document.querySelectorAll(".shopping-item:not(.hidden)")

    if (visibleItems.length === 0) {
      this.shoppingListEl.style.display = "none"
      this.emptyState.style.display = "block"
      this.updateEmptyStateText()
    } else {
      this.shoppingListEl.style.display = "flex"
      this.emptyState.style.display = "none"
    }
  }

  async loadShoppingList() {
    try {
      this.showLoading()
      const response = await fetch("/api/shopping-list")
      const data = await response.json()

      this.shoppingList = data.items || []
      this.lastModified = data.last_modified
      this.renderShoppingList()
      this.updateCategoryCounts() // Make sure counts are updated
      this.updateSyncStatus("synced")
    } catch (error) {
      console.error("Error loading shopping list:", error)
      this.updateSyncStatus("error")
    } finally {
      this.hideLoading()
    }
  }

  async loadTagStats() {
    try {
      const response = await fetch("/api/tag-stats")
      const data = await response.json()
      this.tagStats = data.tag_stats || []
      this.updateCategoryCounts()
    } catch (error) {
      console.error("Error loading tag stats:", error)
    }
  }

  updateCategoryCounts() {
    // Update total count for "all items"
    const totalCountEl = document.getElementById("totalCount")
    if (totalCountEl) {
      totalCountEl.textContent = this.shoppingList.length
    }

    // Count items by category
    const categoryCounts = {}

    // Initialize all categories with 0
    this.categories.forEach(category => {
      categoryCounts[category] = 0
    })

    // Count actual items
    this.shoppingList.forEach(item => {
      const category = item.tag || "אחר"
      if (categoryCounts.hasOwnProperty(category)) {
        categoryCounts[category]++
      } else {
        categoryCounts[category] = 1
      }
    })

    // Update individual category counts in the UI
    Object.entries(categoryCounts).forEach(([category, count]) => {
      const countEl = document.getElementById(`count-${category}`)
      if (countEl) {
        countEl.textContent = count
      }
    })

    console.log("Updated counts:", {
      total: this.shoppingList.length,
      categories: categoryCounts
    })
  }

  startPolling() {
    this.pollInterval = setInterval(async () => {
      try {
        const response = await fetch("/api/shopping-list")
        const data = await response.json()

        if (data.last_modified !== this.lastModified) {
          this.shoppingList = data.items || []
          this.lastModified = data.last_modified
          this.renderShoppingList()
          this.updateCategoryCounts() // Ensure counts are updated on polling
          this.updateSyncStatus("synced")
        }
      } catch (error) {
        console.error("Error polling shopping list:", error)
        this.updateSyncStatus("error")
      }
    }, 2000)
  }

  renderShoppingList() {
    if (!this.shoppingListEl) return

    if (this.shoppingList.length === 0) {
      this.updateEmptyState()
      return
    }

    this.shoppingListEl.innerHTML = this.shoppingList
      .map(item => `
        <div class="shopping-item ${item.completed ? "completed" : ""}"
             data-id="${item.id}"
             data-category="${item.tag || 'אחר'}">
          <div class="item-checkbox ${item.completed ? "checked" : ""}"
               onclick="smartList.toggleItem('${item.id}')">
            ${item.completed ? '<i class="fas fa-check"></i>' : ""}
          </div>
          <div class="item-details">
            <div class="item-name">${this.escapeHtml(item.name)}</div>
            <div class="item-quantity">כמות: ${this.escapeHtml(item.quantity)}</div>
          </div>
          <div class="item-tag">${this.escapeHtml(item.tag || 'אחר')}</div>
          <button class="delete-btn" onclick="smartList.deleteItem('${item.id}')">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      `)
      .join("")

    this.filterShoppingList()
  }

  async toggleItem(itemId) {
    try {
      this.updateSyncStatus("syncing")
      const response = await fetch("/api/toggle-item", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ item_id: itemId }),
      })

      if (response.ok) {
        await this.loadShoppingList()
      } else {
        throw new Error("Failed to toggle item")
      }
    } catch (error) {
      console.error("Error toggling item:", error)
      this.updateSyncStatus("error")
    }
  }

  async deleteItem(itemId) {
    if (!confirm("האם אתה בטוח שברצונך למחוק פריט זה?")) {
      return
    }

    try {
      this.updateSyncStatus("syncing")
      const response = await fetch("/api/remove-item", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ item_id: itemId }),
      })

      if (response.ok) {
        await this.loadShoppingList()
      } else {
        throw new Error("Failed to delete item")
      }
    } catch (error) {
      console.error("Error deleting item:", error)
      this.updateSyncStatus("error")
    }
  }

  async clearAllItems() {
    if (!confirm("האם אתה בטוח שברצונך למחוק את כל הפריטים?")) {
      return
    }

    try {
      this.updateSyncStatus("syncing")
      const response = await fetch("/api/clear-list", {
        method: "POST",
      })

      if (response.ok) {
        await this.loadShoppingList()
      } else {
        throw new Error("Failed to clear list")
      }
    } catch (error) {
      console.error("Error clearing list:", error)
      this.updateSyncStatus("error")
    }
  }

  openAddModal() {
    if (!this.addModal) return
    this.addModal.classList.add("active")
    this.itemName?.focus()
    if (this.itemName) this.itemName.value = ""
    if (this.itemQuantity) this.itemQuantity.value = "1"
    if (this.itemCategory) this.itemCategory.value = "אחר"
  }

  closeAddModal() {
    this.addModal?.classList.remove("active")
  }

  async saveNewItem() {
    if (!this.itemName || !this.itemQuantity || !this.itemCategory) return

    const name = this.itemName.value.trim()
    const quantity = this.itemQuantity.value.trim()
    const tag = this.itemCategory.value

    if (!name) {
      alert("אנא הכנס שם פריט")
      this.itemName.focus()
      return
    }

    try {
      this.updateSyncStatus("syncing")
      const response = await fetch("/api/add-item", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: name,
          quantity: quantity || "1",
          tag: tag,
        }),
      })

      if (response.ok) {
        await this.loadShoppingList()
        this.closeAddModal()
        this.showNotification(`נוסף: ${name} בקטגוריה ${tag}`)
      } else {
        throw new Error("Failed to add item")
      }
    } catch (error) {
      console.error("Error adding item:", error)
      this.updateSyncStatus("error")
      alert("שגיאה בהוספת הפריט")
    }
  }

  async openStatsModal() {
    if (!this.statsModal) return

    try {
      this.showLoading()
      await this.loadTagStats()
      this.renderStats()
      this.statsModal.classList.add("active")
    } catch (error) {
      console.error("Error loading stats:", error)
    } finally {
      this.hideLoading()
    }
  }

  closeStatsModal() {
    this.statsModal?.classList.remove("active")
  }

  renderStats() {
    if (!this.statsContent) return

    const totalItems = this.shoppingList.length
    const completedItems = this.shoppingList.filter(item => item.completed).length
    const pendingItems = totalItems - completedItems
    const completionRate = totalItems > 0 ? (completedItems / totalItems * 100).toFixed(1) : 0

    // General stats
    const generalStatsHtml = `
      <div class="stat-card">
        <h4><i class="fas fa-chart-line"></i> סטטיסטיקות כלליות</h4>
        <div class="stat-row">
          <span class="stat-label">סה״כ פריטים</span>
          <span class="stat-value">${totalItems}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">הושלמו</span>
          <span class="stat-value">${completedItems}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">ממתינים</span>
          <span class="stat-value">${pendingItems}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">אחוז השלמה</span>
          <span class="stat-value">${completionRate}%</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" style="width: ${completionRate}%"></div>
        </div>
      </div>
    `

    // Category stats
    const categoryStats = {}
    this.shoppingList.forEach(item => {
      const category = item.tag || "אחר"
      if (!categoryStats[category]) {
        categoryStats[category] = { total: 0, completed: 0 }
      }
      categoryStats[category].total++
      if (item.completed) {
        categoryStats[category].completed++
      }
    })

    const categoryStatsHtml = `
      <div class="stat-card">
        <h4><i class="fas fa-tags"></i> סטטיסטיקות לפי קטגוריות</h4>
        ${Object.entries(categoryStats)
          .sort(([,a], [,b]) => b.total - a.total)
          .map(([category, stats]) => {
            const rate = (stats.completed / stats.total * 100).toFixed(1)
            return `
              <div class="stat-row">
                <span class="stat-label">${category}</span>
                <span class="stat-value">${stats.total} (${rate}% הושלם)</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill" style="width: ${rate}%"></div>
              </div>
            `
          }).join("")}
      </div>
    `

    this.statsContent.innerHTML = generalStatsHtml + categoryStatsHtml
  }

  updateSyncStatus(status) {
    if (!this.syncStatus) return

    const statusEl = this.syncStatus
    const icon = statusEl.querySelector("i")
    const text = statusEl.querySelector("span")

    statusEl.className = "sync-status"

    switch (status) {
      case "synced":
        statusEl.classList.add("synced")
        if (icon) icon.className = "fas fa-check-circle"
        if (text) text.textContent = "מסונכרן"
        break
      case "syncing":
        statusEl.classList.add("syncing")
        if (icon) icon.className = "fas fa-sync-alt"
        if (text) text.textContent = "מסנכרן..."
        break
      case "error":
        statusEl.classList.add("error")
        if (icon) icon.className = "fas fa-exclamation-triangle"
        if (text) text.textContent = "שגיאה"
        break
    }
  }

  showLoading() {
    this.loadingOverlay?.classList.add("active")
  }

  hideLoading() {
    this.loadingOverlay?.classList.remove("active")
  }

  showNotification(message) {
    const notification = document.createElement("div")
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #27ae60;
      color: white;
      padding: 15px 20px;
      border-radius: 10px;
      font-size: 18px;
      font-weight: 500;
      z-index: 3000;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
      animation: slideInRight 0.3s ease;
      max-width: 400px;
    `
    notification.textContent = message

    document.body.appendChild(notification)

    setTimeout(() => {
      notification.style.animation = "slideOutRight 0.3s ease"
      setTimeout(() => {
        if (document.body.contains(notification)) {
          document.body.removeChild(notification)
        }
      }, 300)
    }, 3000)
  }

  escapeHtml(text) {
    const div = document.createElement("div")
    div.textContent = text
    return div.innerHTML
  }
}

// Add CSS animations for notifications
const style = document.createElement("style")
style.textContent = `
  @keyframes slideInRight {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  @keyframes slideOutRight {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(100%);
      opacity: 0;
    }
  }
`
document.head.appendChild(style)

// Initialize the app
let smartList
document.addEventListener("DOMContentLoaded", () => {
  smartList = new SmartShoppingListWithTags()
})