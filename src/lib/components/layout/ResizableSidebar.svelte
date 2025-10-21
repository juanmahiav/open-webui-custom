<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { showSidebar, mobile } from '$lib/stores';

	let isResizing = false;
	let startX = 0;
	let startWidth = 0;

	const DEFAULT_SIDEBAR_WIDTH = 260; // pixels
	const MIN_SIDEBAR_WIDTH = 200; // pixels
	const MAX_SIDEBAR_WIDTH = 400; // pixels

	// Load saved width from localStorage
	let sidebarWidth = parseInt(localStorage.getItem('sidebarWidth') || DEFAULT_SIDEBAR_WIDTH.toString());

	const handleResizeStart = (e: MouseEvent) => {
		isResizing = true;
		startX = e.clientX;
		startWidth = sidebarWidth;
		document.body.style.cursor = 'col-resize';
		document.body.style.userSelect = 'none';
		document.body.classList.add('resizing');
		e.preventDefault();
	};

	const handleResizeMove = (e: MouseEvent) => {
		if (!isResizing) return;

		const deltaX = e.clientX - startX;
		const newWidth = Math.max(MIN_SIDEBAR_WIDTH, Math.min(MAX_SIDEBAR_WIDTH, startWidth + deltaX));
		
		if (newWidth !== sidebarWidth) {
			sidebarWidth = newWidth;
			localStorage.setItem('sidebarWidth', sidebarWidth.toString());
			
			// Update CSS variable for sidebar width
			document.documentElement.style.setProperty('--sidebar-width', `${sidebarWidth}px`);
		}
	};

	const handleResizeEnd = () => {
		isResizing = false;
		document.body.style.cursor = '';
		document.body.style.userSelect = '';
		document.body.classList.remove('resizing');
	};

	onMount(() => {
		// Set initial CSS variable
		document.documentElement.style.setProperty('--sidebar-width', `${sidebarWidth}px`);
		
		// Add global event listeners for resize
		document.addEventListener('mousemove', handleResizeMove);
		document.addEventListener('mouseup', handleResizeEnd);
	});

	onDestroy(() => {
		document.removeEventListener('mousemove', handleResizeMove);
		document.removeEventListener('mouseup', handleResizeEnd);
		if (isResizing) {
			document.body.classList.remove('resizing');
		}
	});
</script>

{#if $mobile}
	<!-- Mobile: Use existing sidebar behavior -->
	<div class="flex w-full h-full">
		{#if $showSidebar}
			<div class="fixed inset-0 z-40 md:hidden">
				<div 
					class="fixed inset-0 bg-black/60 w-full h-full"
					on:mousedown={() => showSidebar.set(false)}
				/>
			</div>
		{/if}
		
		<div 
			class="fixed md:hidden z-50 top-0 left-0 h-screen transition-transform duration-300 {$showSidebar ? 'translate-x-0' : '-translate-x-full'}"
			style="width: {sidebarWidth}px; max-width: 85vw;"
		>
			<slot name="sidebar" />
		</div>
		
		<div class="flex-1 w-full">
			<slot name="main" />
		</div>
	</div>
{:else}
	<!-- Desktop: Use resizable sidebar -->
	<div class="flex w-full h-full">
		{#if $showSidebar}
			<div 
				class="relative flex-shrink-0 h-screen"
				style="width: {sidebarWidth}px;"
			>
				<slot name="sidebar" />
				
				<!-- Resize handle -->
				<div
					class="absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-blue-500/20 transition-colors z-50 group"
					on:mousedown={handleResizeStart}
				>
					<div class="absolute top-1/2 right-0 w-0.5 h-8 bg-gray-300 dark:bg-gray-600 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity" />
				</div>
			</div>
		{/if}
		
		<div class="flex-1 min-w-0">
			<slot name="main" />
		</div>
	</div>
{/if}

<style>
	/* Ensure the resize handle is always visible and interactive */
	.resize-handle {
		position: relative;
	}
	
	.resize-handle:hover::after {
		content: '';
		position: absolute;
		top: 0;
		right: 0;
		width: 4px;
		height: 100%;
		background: rgba(59, 130, 246, 0.2);
		cursor: col-resize;
	}
	
	/* Prevent text selection during resize */
	:global(body.resizing) {
		cursor: col-resize !important;
		user-select: none !important;
	}
</style>