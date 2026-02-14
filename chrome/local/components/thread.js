function Task(name, delay, exec) {
	// overwrite this function
	this.exec = exec || function (task, resolve) { resolve(); };
	this.name = name;
	this.delay = delay || 0;
}

function Thread() {
	this.tasks = [];
	this.runing = false;
	this.curTaskBeginTime = 0;
	this.intervalTime = 500;
}

Thread.prototype.start = function(intervalTime) {
	if (this.runing) {
		return;
	}
	this.curTaskBeginTime = Date.now();
	this.intervalTime = intervalTime || 500;
	this.runing = true;
	this._wait();
}

Thread.prototype._wait = function() {
	let rr = () => this._run();
	setTimeout(rr, this.intervalTime);
}

Thread.prototype._run = function() {
	if (! this.runing) {
		return; // stop
	}
	if (this.tasks.length == 0) {
		this._wait();
		return;
	}
	let topTask = this.tasks[0];
	let diffTime = Date.now() - this.curTaskBeginTime;
	if (diffTime < topTask.delay) {
		// console.log('Wait...');
		// wait
		this._wait();
		return;
	}
	let curTask = this.tasks.shift();
	curTask.exec(curTask, () => this._resolve());
}

Thread.prototype._resolve = function() {
	this.curTaskBeginTime = Date.now();
	this._run(); // run next task
}

Thread.prototype.stop = function() {
	this.runing = false;
	this.curTaskBeginTime = 0;
}

// exec: function(resolve, reject) 
// when finish call resolve() or reject()
Thread.prototype.addTask = function(task) {
	this.tasks.push(task);
}

Thread.prototype.insertTask = function (idx, task) {
	this.tasks.splice(idx, 0, task);
}

Thread.prototype.addUniqueTask = function(uniqueId, task) {
	if (! task) {
		return;
	}
	for (let i = 0; i < this.tasks.length; i++) {
		let tk = this.tasks[i];
		if (tk['__unique_id__'] && tk['__unique_id__'] == uniqueId) {
			return;
		}
	}
	if (uniqueId != null) {
		task['__unique_id__'] = uniqueId;
	}
	
	this.tasks.push(task);
}

class ThreadPool {
	constructor(size = 10) {
		this.pools = [];
		this.tasks = [];
		for (let i = 0; i < size; i++) {
			this.pools.push(new Thread());
			// share tasks queue
			this.pools[i].tasks = this.tasks;
		}
	}

	start() {
		for (let t of this.pools) {
			t.start();
		}
	}

	addTask(task) {
		this.tasks.push(task);
	}
}

export {
	Thread, Task, ThreadPool
}