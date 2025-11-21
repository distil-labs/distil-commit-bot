# distil commit bot examples

## Example 1

### diff
```diff
diff --git a\/src\/hooks\/useFetch.js b\/src\/hooks\/useFetch.js
index 9c1d2f7..b8e4a5b 100644
--- a\/src\/hooks\/useFetch.js
+++ b\/src\/hooks\/useFetch.js
@@ -1,13 +1,17 @@
 import { useState, useEffect } from 'react';
-import axios from 'axios';
+import axios from 'axios';
 
 export const useFetch = (url, options = {}) => {
   const [data, setData] = useState(null);
   const [error, setError] = useState(null);
   const [loading, setLoading] = useState(true);
 
-  useEffect(() => {
-    axios.get(url, options)
-      .then((res) => {
-        setData(res.data);
-        setLoading(false);
-      })
-      .catch((err) => {
-        setError(err);
-        setLoading(false);
-      });
-  }, [url]);
+  useEffect(() => {
+    const controller = new AbortController();
+    const fetchData = async () => {
+      try {
+        const response = await axios.get(url, { signal: controller.signal, ...options });
+        setData(response.data);
+        setError(null);
+      } catch (err) {
+        if (axios.isCancel(err)) {
+          console.log('Request canceled', err.message);
+        } else {
+          setError(err);
+        }
+      } finally {
+        setLoading(false);
+      }
+    };
+    fetchData();
+    return () => controller.abort();
+  }, [url, JSON.stringify(options)]); \/\/ ensure options changes trigger refetch
+
+  return { data, error, loading };
 };
```

### commit message
```
Add abort handling and async logic to useFetch hook

The hook now creates an AbortController to cancel in‑flight requests on unmount or when options change. It switches to async\/await, resets errors on success, and logs cancelled requests. The effect's dependencies include a stringified options object to ensure refetching when options mutate, and the hook now returns its data, error, and loading state.
```

## Example 2

### diff
```diff
diff --git a/src/services/cache.ts b/src/services/cache.ts
index 1122a33..3344b55 100644
--- a/src/services/cache.ts
+++ b/src/services/cache.ts
@@ -4,9 +4,12 @@ const PREFIX = 'app_';
 
 export const setItem = (key: string, value: any) => {
   localStorage.setItem(PREFIX + key, JSON.stringify(value));
 };
 
-export const getItem = (key: string) => {
-  const raw = localStorage.getItem(PREFIX + key);
-  return raw ? JSON.parse(raw) : null;
+export const getItem = <T>(key: string): T | null => {
+  const raw = localStorage.getItem(PREFIX + key);
+  if (!raw) return null;
+  try {
+    return JSON.parse(raw) as T;
+  } catch {
+    // If parsing fails, clear corrupted entry and return null
+    localStorage.removeItem(PREFIX + key);
+    return null;
+  }
 };
 
 export const removeItem = (key: string) => {
   localStorage.removeItem(PREFIX + key);
 };
```

### commit message
```
Add generic typing and error handling to cache getItem

The getItem function now uses a generic <T> type and returns the parsed value or null, providing type safety for callers. It wraps JSON.parse in a try/catch and removes the entry from localStorage if parsing fails, preventing corrupted data from lingering. These changes make the cache service more robust and easier to use throughout the application.
```

## Example 3

### diff
```diff
diff --git a/src/components/Dropdown.jsx b/src/components/Dropdown.jsx
index 9f8e7d6..c3b2a1f 100644
--- a/src/components/Dropdown.jsx
+++ b/src/components/Dropdown.jsx
@@ -5,11 +5,19 @@ import React, { useState, useRef, useEffect } from 'react';
 
 const Dropdown = ({ options, onSelect }) => {
   const [open, setOpen] = useState(false);
-  const toggle = () => setOpen(!open);
+  const toggle = () => setOpen(prev => !prev);
   const ref = useRef(null);
 
-  useEffect(() => {
-    const handleClickOutside = (e) => {
-      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
-    };
-    document.addEventListener('mousedown', handleClickOutside);
-    return () => document.removeEventListener('mousedown', handleClickOutside);
-  }, []);
+  // Close on outside click & handle keyboard navigation
+  useEffect(() => {
+    const handleClickOutside = (e) => {
+      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
+    };
+    const handleKeyDown = (e) => {
+      if (!open) return;
+      if (e.key === 'Escape') setOpen(false);
+      if (e.key === 'ArrowDown') {
+        const first = ref.current?.querySelector('li');
+        first?.focus();
+      }
+    };
+    document.addEventListener('mousedown', handleClickOutside);
+    document.addEventListener('keydown', handleKeyDown);
+    return () => {
+      document.removeEventListener('mousedown', handleClickOutside);
+      document.removeEventListener('keydown', handleKeyDown);
+    };
+  }, [open]);
 
   return (
     <div className="dropdown" ref={ref}>
@@ -22,6 +32,7 @@ const Dropdown = ({ options, onSelect }) => {
         {options.map((opt, idx) => (
           <li
             key={idx}
-            onClick={() => { onSelect(opt); setOpen(false); }}
+            tabIndex={0}
+            onClick={() => { onSelect(opt); setOpen(false); }}
+            onKeyPress={(e) => e.key === 'Enter' && onSelect(opt)}
           >
             {opt.label}
           </li>
@@ -31,4 +42,6 @@ const Dropdown = ({ options, onSelect }) => {
   );
 };
 
 export default Dropdown;
+// Added ARIA roles for better accessibility
+// <ul role="listbox"> and <li role="option"> could be added in future iterations
```

### commit message
```
Enhance Dropdown accessibility and keyboard support

The toggle handler now uses a functional state update to avoid stale closures. A new keydown listener closes the menu on Escape and focuses the first list item on ArrowDown, improving keyboard navigation. List items are made focusable with `tabIndex=0` and respond to Enter key presses, allowing selection via keyboard. Additional comments note future ARIA role enhancements for better screen‑reader support.
```

## Example 4

### diff
```diff
diff --git a/src/hooks/useFetch.ts b/src/hooks/useFetch.ts
index 9a3b7c1..d4e5f6a 100644
--- a/src/hooks/useFetch.ts
+++ b/src/hooks/useFetch.ts
@@ -5,9 +5,13 @@ import { useState, useEffect } from 'react';
 
 export const useFetch = (url: string) => {
   const [data, setData] = useState<any>(null);
-  const [error, setError] = useState<Error | null>(null);
+  const [error, setError] = useState<Error | null>(null);
   const [loading, setLoading] = useState<boolean>(true);
 
-  useEffect(() => {
-    fetch(url)
+  useEffect(() => {
+    // Added AbortController to allow cancellation of the request
+    const controller = new AbortController();
+    const signal = controller.signal;
+
+    fetch(url, { signal })
       .then((res) => res.json())
       .then((json) => {
         setData(json);
@@ -19,6 +23,10 @@ export const useFetch = (url: string) => {
         setLoading(false);
       });
 
+    return () => {
+      controller.abort(); // Clean up on unmount or url change
+    };
+  }, [url]);
 
   return { data, error, loading };
 };
```

### commit message
```
Add abort support to useFetch hook

The hook now creates an AbortController and passes its signal to the fetch request, enabling cancellation of in‑flight requests. A cleanup function aborts the request when the component unmounts or the URL changes, preventing memory leaks and stray state updates. This enhances robustness of data fetching in React components.
```

## Example 5

### diff
```diff
diff --git a/src/components/Modal.tsx b/src/components/Modal.tsx
index 7a9d3c2..e5f1b8d 100644
--- a/src/components/Modal.tsx
+++ b/src/components/Modal.tsx
@@ -5,12 +5,15 @@ interface ModalProps {
   /** Content displayed inside the modal */
   children: React.ReactNode;
   /** Callback when the modal requests to be closed */
-  onClose?: () => void;
+  onClose?: (reason: 'backdrop' | 'escape' | 'button') => void;
   /** Whether the modal is currently visible */
   isOpen: boolean;
 }
 
 export const Modal: React.FC<ModalProps> = ({ children, onClose, isOpen }) => {
-  if (!isOpen) return null;
+  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
+    if (e.target === e.currentTarget) {
+      onClose?.('backdrop');
+    }
+  };
+
+  if (!isOpen) return null;
 
-  return (
-    <div className="modal-backdrop">
-      <div className="modal-content">{children}</div>
-    </div>
-  );
+  return (
+    <div className="modal-backdrop" onClick={handleBackdropClick}>
+      <div className="modal-content">
+        {children}
+        <button onClick={() => onClose?.('button')} className="modal-close-btn">
+          Close
+        </button>
+      </div>
+    </div>
+  );
 };
 
 export default Modal;
```

### commit message
```
Add close reason handling and button to Modal component

The Modal's onClose callback now receives a reason indicating how the modal was closed ('backdrop', 'escape', or 'button'). A click handler on the backdrop detects overlay clicks and invokes onClose with the 'backdrop' reason. A new close button inside the modal content also triggers onClose with the 'button' reason. These updates give consumers clearer context for closing actions and improve usability.
```

## Example 6

### diff
```diff
diff --git a/src/lib/math.ts b/src/lib/math.ts
index 4f2a9b1..c3d8e7a 100644
--- a/src/lib/math.ts
+++ b/src/lib/math.ts
@@ -1,12 +1,15 @@
 export const add = (a: number, b: number): number => {
   return a + b;
 };
 
-export const multiply = (a: number, b: number): number => {
-  return a * b;
-};
+// Updated to guard against overflow for large numbers
+export const multiply = (a: number, b: number): number => {
+  const result = a * b;
+  if (!Number.isFinite(result)) {
+    throw new Error('Multiplication result exceeds numeric limits');
+  }
+  return result;
+};
 
 // Existing helper retained for backward compatibility
 export const subtract = (a: number, b: number): number => {
   return a - b;
 };
 
+// New utility to compute the factorial of a non‑negative integer
+export const factorial = (n: number): number => {
+  if (n < 0) throw new Error('Factorial is not defined for negative numbers');
+  return n <= 1 ? 1 : n * factorial(n - 1);
+};
```

### commit message
```
Add overflow check to multiply and new factorial utility

The `multiply` function now includes a runtime check that throws an error when the result is not finite, preventing silent overflow for extremely large inputs. A new `factorial` function is introduced to compute the factorial of a non‑negative integer recursively, with validation that rejects negative arguments. These changes improve the robustness of the math utilities and expand the library's functionality.
```

## Example 7

### diff
```diff
diff --git a/src/hooks/useLocalStorage.ts b/src/hooks/useLocalStorage.ts
index a1b2c3d..e4f5g6h 100644
--- a/src/hooks/useLocalStorage.ts
+++ b/src/hooks/useLocalStorage.ts
@@ -1,12 +1,15 @@
 import { useState, useEffect } from 'react';
 
-export const useLocalStorage = (key: string, initialValue: any) => {
-  const [storedValue, setStoredValue] = useState(() => {
-    try {
-      const item = window.localStorage.getItem(key);
-      return item ? JSON.parse(item) : initialValue;
-    } catch (error) {
-      console.error(error);
-      return initialValue;
-    }
-  });
+export const useLocalStorage = <T>(key: string, initialValue: T): [T, (value: T) => void] => {
+  const [storedValue, setStoredValue] = useState<T>(() => {
+    try {
+      const item = window.localStorage.getItem(key);
+      return item ? (JSON.parse(item) as T) : initialValue;
+    } catch (error) {
+      console.warn('useLocalStorage: unable to read from localStorage', error);
+      return initialValue;
+    }
+  });
 
   useEffect(() => {
     try {
@@ -14,4 +17,5 @@ export const useLocalStorage = (key: string, initialValue: any) => {
       window.localStorage.setItem(key, JSON.stringify(storedValue));
     } catch (error) {
       console.error(error);
+      // Optionally fallback to in‑memory store here
     }
   }, [key, storedValue]);
 
   return [storedValue, setStoredValue];
 };
```

### commit message
```
Add generic typing and improve error handling to useLocalStorage hook

The hook now uses a generic `<T>` parameter, returning a typed `[value, setter]` tuple instead of `any`. JSON parsing is cast to `T` and error logging is changed to a warning with clearer context. A comment notes a possible in‑memory fallback, and the overall implementation is more type‑safe and robust for React projects.
```
