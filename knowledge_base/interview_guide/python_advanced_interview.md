# Python 高级编程面试专题

## Python 核心机制

### GIL（全局解释器锁）

GIL 是 CPython 实现中的一个互斥锁，确保同一时刻只有一个线程执行 Python 字节码。

**为什么需要 GIL？** CPython 的内存管理（引用计数）不是线程安全的，GIL 简化了内存管理的实现。

**影响：**
- CPU 密集型任务无法利用多核 → 用 multiprocessing
- I/O 密集型任务多线程仍然有效 → I/O 等待时释放 GIL

**绕过 GIL 的方案：**
- multiprocessing 模块（多进程）
- C 扩展 / Cython（在 C 层释放 GIL）
- asyncio（协程，单线程并发）
- subprocess / multiprocessing.Pool

### 装饰器深入

装饰器本质是高阶函数，可以带参数、可以堆叠：

```python
# 带参数的装饰器
def retry(max_retries=3, delay=1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay)
        return wrapper
    return decorator

@retry(max_retries=5, delay=2)
def fetch_data(url):
    # 可能失败的网络请求
    pass
```

**类装饰器：** 用类实现 __call__ 方法
**functools.wraps：** 保留被装饰函数的元信息（__name__, __doc__）

### 生成器与迭代器

**生成器的优势：**
- 惰性求值：按需生成元素，节省内存
- 处理大数据：可以逐行读取超大文件
- 无限序列：可以表示数学上的无限序列

```python
# 生成器函数
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

# 生成器表达式
squares = (x*x for x in range(1000000))  # 不占内存
sum(squares)  # 惰性计算

# 生成器的 send/throw/close
def echo_generator():
    while True:
        received = yield
        print(f"Received: {received}")

gen = echo_generator()
next(gen)       # 启动生成器
gen.send("hello")  # 发送值
```

### 上下文管理器

两种实现方式：

```python
# 方式一：类实现
class DatabaseConnection:
    def __enter__(self):
        self.conn = create_connection()
        return self.conn
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

# 方式二：contextlib
from contextlib import contextmanager

@contextmanager
def timer(name):
    start = time.time()
    yield
    print(f"{name}: {time.time()-start:.2f}s")
```

## Python 并发编程

### threading vs multiprocessing vs asyncio

| 特性 | threading | multiprocessing | asyncio |
|------|-----------|-----------------|---------|
| 并发类型 | 多线程 | 多进程 | 协程 |
| GIL 影响 | 受限 | 不受 | 单线程 |
| 内存开销 | 共享内存 | 独立内存 | 最小 |
| 适用场景 | I/O 密集 | CPU 密集 | I/O 密集 |
| 通信方式 | 共享变量+锁 | Queue/Pipe | await |
| 创建开销 | 小 | 大 | 最小 |

### asyncio 协程

```python
import asyncio

async def fetch_url(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

async def main():
    urls = ["http://a.com", "http://b.com", "http://c.com"]
    # 并发请求
    tasks = [fetch_url(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return results
```

### 线程安全

**锁的使用：**
```python
from threading import Lock

lock = Lock()
def safe_increment():
    with lock:
        counter += 1
```

**常见并发问题：**
- 竞态条件（Race Condition）
- 死锁（Deadlock）：避免嵌套锁
- 活锁（Livelock）
- 饥饿（Starvation）

## Python 高级特性

### 元类（Metaclass）

元类是类的类，控制类的创建过程：

```python
class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Database(metaclass=SingletonMeta):
    pass
```

### 描述符（Descriptor）

实现 __get__、__set__、__delete__ 的类，用于属性访问控制：

```python
class ValidatedAttribute:
    def __init__(self, name, validator):
        self.name = name
        self.validator = validator
    def __set_name__(self, owner, name):
        self.storage_name = name
    def __get__(self, obj, objtype=None):
        return obj.__dict__.get(self.storage_name)
    def __set__(self, obj, value):
        if not self.validator(value):
            raise ValueError(f"Invalid {self.name}")
        obj.__dict__[self.storage_name] = value
```

### __new__ vs __init__

- __new__：创建实例（类方法），负责分配内存
- __init__：初始化实例（实例方法），负责设置属性
- __new__ 在 __init__ 之前调用，用于实现单例、继承不可变类型等

### Python 内存管理

- 引用计数（主要机制）
- 分代垃圾回收（处理循环引用）
- 三代：generation 0/1/2，存活越久的对象检查频率越低
- gc.get_threshold() 可查看阈值
- weakref 弱引用避免循环引用

## Python Web 开发高频题

### FastAPI 核心

- 基于 Starlette + Pydantic，原生支持 async/await
- 自动生成 OpenAPI 文档
- 依赖注入系统（Depends）
- 中间件（Middleware）

### SQLAlchemy 核心

- ORM 模式 vs Core 模式
- Session 管理（scoped_session）
- 关系映射（一对一、一对多、多对多）
- 惰性加载 vs 预加载（joinedload / selectinload）

### 常见设计模式

- 单例模式（数据库连接池）
- 工厂模式（对象创建解耦）
- 观察者模式（事件系统）
- 策略模式（算法替换）
- 装饰器模式（AOP 横切关注点）
